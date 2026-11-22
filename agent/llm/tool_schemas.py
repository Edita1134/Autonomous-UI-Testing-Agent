"""Tool definitions offered to the LLM (OpenAI-style function format; llm/client.py converts them for Gemini).

Every tool requires a `thought` field: the model must state why it is acting.
That sentence is logged as the agent's reasoning trail (see evidence/logs).
"""

FINISH_STEP = "finish_step"

_ELEMENT_PROPERTIES = {
    "role": {
        "type": "string",
        "description": "ARIA role of the element as shown in the page snapshot, e.g. button, link, textbox, "
        "checkbox. Use 'text' only for plain non-interactive text.",
    },
    "name": {"type": "string", "description": "Accessible name exactly as shown in the page snapshot."},
    "within_text": {
        "type": "string",
        "description": "Optional. Only set this after an error says several elements match: text near the "
        "wanted element (e.g. a product name) to tell it apart from the others.",
    },
}


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "One sentence: what you see and why you act."},
                    **properties,
                },
                "required": ["thought", *required],
            },
        },
    }


TOOL_SCHEMAS = [
    _tool("navigate", "Open a URL.", {"url": {"type": "string"}}, ["url"]),
    _tool("click", "Click an element.", _ELEMENT_PROPERTIES, ["role", "name"]),
    _tool(
        "fill",
        "Type text into an input, replacing its content.",
        {**_ELEMENT_PROPERTIES, "value": {"type": "string"}},
        ["role", "name", "value"],
    ),
    _tool("press_key", "Press a keyboard key, e.g. Enter.", {"key": {"type": "string"}}, ["key"]),
    _tool(
        FINISH_STEP,
        "Declare the current step finished. Use 'done' only if the page now shows the step's goal "
        "achieved; use 'blocked' if it cannot be done.",
        {
            "status": {"type": "string", "enum": ["done", "blocked"]},
            "summary": {"type": "string", "description": "What happened, citing what you see on the page."},
        },
        ["status", "summary"],
    ),
]
