"""Unit tests for the Gemini adapter that need no network or API key."""

from google.genai import types

from agent.llm.client import _declaration, _parse_reply, _split_messages, _suggested_delay
from agent.llm.client import MalformedToolCallError
from agent.llm.tool_schemas import TOOL_SCHEMAS

import pytest


def test_messages_are_split_into_system_text_and_user_contents():
    system, contents = _split_messages(
        [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hello"}]
    )
    assert system == "be brief"
    assert [content.role for content in contents] == ["user"]
    assert contents[0].parts[0].text == "hello"


def test_every_tool_schema_converts_to_a_gemini_declaration():
    names = [_declaration(tool).name for tool in TOOL_SCHEMAS]
    assert names == ["navigate", "click", "fill", "press_key", "finish_step"]


def test_tool_call_is_read_from_a_reply():
    reply = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name="click", args={"role": "button", "name": "Login"}))],
                ),
                finish_reason=types.FinishReason.STOP,
            )
        ]
    )
    parsed = _parse_reply(reply)
    assert parsed.tool_calls[0].name == "click"
    assert parsed.tool_calls[0].arguments == {"role": "button", "name": "Login"}


def test_malformed_tool_call_is_reported_not_crashed():
    reply = types.GenerateContentResponse(
        candidates=[types.Candidate(finish_reason=types.FinishReason.MALFORMED_FUNCTION_CALL)]
    )
    with pytest.raises(MalformedToolCallError):
        _parse_reply(reply)


def test_daily_quota_delay_in_hours_is_understood():
    assert _suggested_delay(Exception("Please retry in 17h38m45.9s.")) == pytest.approx(17 * 3600 + 38 * 60 + 46.9)


def test_retry_delay_is_read_from_a_rate_limit_message():
    assert _suggested_delay(Exception("429 RESOURCE_EXHAUSTED. Please retry in 23.4s.")) == pytest.approx(24.4)
    assert _suggested_delay(Exception("some other error")) == 0.0


def test_model_name_without_the_gemini_prefix_is_fixed():
    from agent.config import _normalise_model

    assert _normalise_model("3.5-flash-lite") == "gemini-3.5-flash-lite"
    assert _normalise_model("models/gemini-3.5-flash") == "gemini-3.5-flash"
    assert _normalise_model("  ") == "gemini-3.5-flash-lite"
