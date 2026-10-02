"""Gemini-backed brain: understands requests and drives the skill system.

Flow for one request:
    user text -> Gemini (with the list of skills as tools)
        -> Gemini asks to call a skill (function call)
        -> we run it (confirming destructive ones) and send the result back
        -> repeat until Gemini returns a final text answer.

Function calls are executed *manually* (not by the SDK's auto-calling) so every
destructive action passes through our confirmation gate first.
"""
from __future__ import annotations

from google import genai
from google.genai import types

import config
from assistant import registry
from assistant.brain.base import Brain

# JSON-schema type name -> Gemini Schema type enum.
_TYPE_MAP = {
    "string": types.Type.STRING,
    "integer": types.Type.INTEGER,
    "number": types.Type.NUMBER,
    "boolean": types.Type.BOOLEAN,
    "array": types.Type.ARRAY,
    "object": types.Type.OBJECT,
}

_SYSTEM_INSTRUCTION = """\
You are a capable voice/text assistant that operates the user's Windows PC on \
their behalf, similar to "Jarvis". You carry out requests by calling the tools \
(skills) available to you — opening apps, controlling the mouse and keyboard, \
managing files, searching the web, and more.

Guidelines:
- Take real action with tools; don't just describe what could be done.
- Prefer a specific skill when one fits. Use `run_python` only as a fallback when \
no other skill can accomplish the task.
- Use absolute file paths. The user's key folders are listed below.
- Destructive actions (deleting/overwriting files, closing apps, shutting down, \
running shell commands or code) are automatically shown to the user for approval, \
so you don't need to ask again — but DO make sure the target (path, app, command) \
is exactly what the user wants. If a request is ambiguous or risky, ask a brief \
clarifying question instead of guessing.
- You can chain multiple tool calls to complete a task.
- Keep replies short and natural — they may be read aloud. After acting, confirm \
briefly what you did.

Environment:
{environment}
"""


def _to_schema(js: dict) -> types.Schema:
    """Convert a plain JSON-schema dict into a Gemini types.Schema."""
    jtype = js.get("type", "string")
    schema = types.Schema(type=_TYPE_MAP.get(jtype, types.Type.STRING))
    if "description" in js:
        schema.description = js["description"]
    if "enum" in js:
        schema.enum = js["enum"]
    if jtype == "object":
        props = js.get("properties", {})
        schema.properties = {k: _to_schema(v) for k, v in props.items()}
        if js.get("required"):
            schema.required = js["required"]
    if jtype == "array" and "items" in js:
        schema.items = _to_schema(js["items"])
    return schema


def _build_tools() -> list[types.Tool]:
    declarations = []
    for sk in registry.all_skills():
        declarations.append(
            types.FunctionDeclaration(
                name=sk.name,
                description=sk.description,
                parameters=_to_schema(sk.parameters),
            )
        )
    return [types.Tool(function_declarations=declarations)]


def _text_parts(content) -> str:
    parts = getattr(content, "parts", None) or []
    return "".join(p.text for p in parts if getattr(p, "text", None))


def _function_calls(content) -> list:
    parts = getattr(content, "parts", None) or []
    return [p.function_call for p in parts if getattr(p, "function_call", None)]


class GeminiBrain(Brain):
    def __init__(self) -> None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your "
                "key from https://aistudio.google.com/apikey"
            )
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self._config = types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION.format(
                environment=config.environment_summary()
            ),
            tools=_build_tools(),
            # We run functions ourselves so we can confirm destructive ones.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        self._history: list[types.Content] = []

    def reset(self) -> None:
        self._history = []

    def ask(self, user_text: str) -> str:
        self._history.append(
            types.Content(role="user", parts=[types.Part(text=user_text)])
        )

        for _ in range(config.MAX_STEPS):
            try:
                response = self._client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=self._history,
                    config=self._config,
                )
            except Exception as exc:  # noqa: BLE001
                return f"(Gemini request failed: {exc})"

            candidates = getattr(response, "candidates", None) or []
            if not candidates:
                return "(No response from Gemini — it may have been blocked.)"

            model_content = candidates[0].content
            self._history.append(model_content)

            calls = _function_calls(model_content)
            if not calls:
                # No tool calls -> this is the final natural-language answer.
                return _text_parts(model_content) or "(Done.)"

            # Execute each requested skill and feed results back to Gemini.
            response_parts = []
            for fc in calls:
                args = dict(fc.args) if fc.args else {}
                result = registry.execute_skill(fc.name, args)
                response_parts.append(
                    types.Part.from_function_response(
                        name=fc.name, response={"result": result}
                    )
                )
            self._history.append(
                types.Content(role="user", parts=response_parts)
            )

        return (
            "(Stopped after reaching the maximum number of steps. "
            "The task may be only partly done.)"
        )
