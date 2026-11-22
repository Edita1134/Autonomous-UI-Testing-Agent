"""Thin wrapper around the Gemini Developer API (function calling and JSON mode).

Handles the things that go wrong most often with hosted models: rate limits and temporary server
errors (retry with backoff, honouring the delay Gemini suggests) and malformed tool calls (surfaced as
an error the executor can recover from instead of crashing the run).
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field

import httpx
from google import genai
from google.genai import errors, types

from agent.config import Settings

log = logging.getLogger("agent.llm")

REQUEST_TIMEOUT_MS = 60_000  # Without a timeout one stuck request can hang a run forever.
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 5
MAX_WAIT_SECONDS = 60
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
# Gemini models "think" before answering. Little thinking keeps each browser turn fast;
# planning and judging get more room to reason. (2.5 models take a token budget, 3.x a level.)
TOOL_TURN_THINKING = ("low", 512)
JSON_TURN_THINKING = ("medium", 2048)

_RETRY_HINT_RE = re.compile(r"(?:retry in\s+|retryDelay\W+)((?:\d+h)?(?:\d+m)?[\d.]+s)", re.IGNORECASE)
_DURATION_RE = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?([\d.]+)s")
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class QuotaExhaustedError(RuntimeError):
    """The API quota is used up for a long time (e.g. the free tier's daily limit); retrying would not help."""


class MalformedToolCallError(Exception):
    """The model produced a tool call that could not be used."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient:
    def __init__(self, settings: Settings):
        self._client = genai.Client(
            api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
        )
        self._model = settings.model

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMReply:
        """One chat turn. With `tools`, the model must answer with a tool call."""
        options: dict = {}
        if tools:
            options["tools"] = [types.Tool(function_declarations=[_declaration(tool) for tool in tools])]
            options["tool_config"] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode=types.FunctionCallingConfigMode.ANY)
            )
        response = self._generate(messages, TOOL_TURN_THINKING, **options)
        return _parse_reply(response)

    def chat_json(self, messages: list[dict]) -> dict:
        """One chat turn that must return a JSON object (prompts must mention JSON)."""
        response = self._generate(messages, JSON_TURN_THINKING, response_mime_type="application/json")
        text = _JSON_FENCE_RE.sub("", _reply_text(response).strip())
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model returned invalid JSON: {text[:200]!r}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Model returned JSON that is not an object: {text[:200]!r}")
        return data

    # ---- Internals ---------------------------------------------------------------

    def _generate(self, messages: list[dict], thinking: tuple[str, int], **options):
        system_text, contents = _split_messages(messages)
        if thinking_config := _thinking_config(self._model, *thinking):
            options["thinking_config"] = thinking_config
        config = types.GenerateContentConfig(system_instruction=system_text, temperature=0, **options)

        for attempt in range(MAX_RETRIES + 1):
            try:
                return self._client.models.generate_content(model=self._model, contents=contents, config=config)
            except (errors.APIError, httpx.TransportError) as exc:
                if attempt == MAX_RETRIES or not _is_retryable(exc):
                    raise
                suggested = _suggested_delay(exc)
                if suggested > MAX_WAIT_SECONDS:  # Daily quota: waiting a few minutes cannot fix it.
                    raise QuotaExhaustedError(
                        f"Gemini quota for {self._model} is used up; it resets in about {_describe(suggested)}. "
                        "Set GEMINI_MODEL to another model (e.g. gemini-3.5-flash-lite) or enable billing."
                    ) from exc
                delay = min(suggested or BACKOFF_BASE_SECONDS * 2**attempt, MAX_WAIT_SECONDS)
                reason = f"{exc.code} {exc.status}" if isinstance(exc, errors.APIError) else type(exc).__name__
                log.warning("Gemini %s; retrying in %.0fs", reason, delay)
                time.sleep(delay)


def _thinking_config(model: str, level: str, budget: int) -> types.ThinkingConfig | None:
    if model.startswith("gemini-2.5"):
        return types.ThinkingConfig(thinking_budget=budget)
    if model.startswith("gemini-3"):
        return types.ThinkingConfig(thinking_level=level)
    return None  # Unknown model family: use its defaults.


def _split_messages(messages: list[dict]) -> tuple[str, list[types.Content]]:
    """Our prompts are OpenAI-style {role, content}; Gemini wants the system text separate."""
    system_text = "\n\n".join(message["content"] for message in messages if message["role"] == "system")
    contents = [
        types.Content(
            role="model" if message["role"] == "assistant" else "user",
            parts=[types.Part(text=message["content"])],
        )
        for message in messages
        if message["role"] != "system"
    ]
    return system_text, contents


def _declaration(tool: dict) -> types.FunctionDeclaration:
    """Convert our OpenAI-style tool definition (see tool_schemas.py) into a Gemini one."""
    function = tool["function"]
    return types.FunctionDeclaration(
        name=function["name"],
        description=function["description"],
        parameters_json_schema=function["parameters"],
    )


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, errors.APIError):
        return exc.code in RETRYABLE_STATUS_CODES
    return True  # Network-level failure.


def _suggested_delay(exc: Exception) -> float:
    """Gemini's 429 responses say how long to wait ("Please retry in 23.4s"); 0 if it did not."""
    match = _RETRY_HINT_RE.search(str(exc))
    if not match:
        return 0.0
    hours, minutes, seconds = _DURATION_RE.fullmatch(match.group(1)).groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + float(seconds) + 1  # Plus a second of margin.


def _describe(seconds: float) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    return f"{hours}h {remainder // 60}m" if hours else f"{remainder // 60}m"


def _reply_text(response) -> str:
    candidate = response.candidates[0] if response.candidates else None
    parts = candidate.content.parts if candidate and candidate.content and candidate.content.parts else []
    return "".join(part.text for part in parts if part.text and not part.thought)


def _parse_reply(response) -> LLMReply:
    candidate = response.candidates[0] if response.candidates else None
    if candidate is not None and candidate.finish_reason == types.FinishReason.MALFORMED_FUNCTION_CALL:
        raise MalformedToolCallError(candidate.finish_message or "Gemini could not form a valid tool call.")
    calls = [
        ToolCall(name=call.name, arguments=dict(call.args or {})) for call in (response.function_calls or [])
    ]
    return LLMReply(content=_reply_text(response), tool_calls=calls)
