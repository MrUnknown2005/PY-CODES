"""Skill registry — the heart of the tool system.

Any function decorated with `@skill(...)` becomes an ability the brain can call.
The registry stays deliberately *brain-neutral*: it stores a plain JSON-schema
description of each skill's parameters. Each brain (Gemini today, maybe Ollama or
Claude later) is responsible for translating that schema into its own format.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

import config
from assistant import safety
from assistant.confirm import confirm_action

# Map Python type hints to JSON-schema type names.
_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


@dataclass
class Skill:
    name: str
    func: Callable[..., Any]
    description: str
    parameters: dict  # JSON-schema object describing the arguments
    destructive: bool = False


_SKILLS: dict[str, Skill] = {}


def _build_parameters(func: Callable, descriptions: dict[str, str]) -> dict:
    """Derive a JSON-schema `object` from the function signature + hints."""
    sig = inspect.signature(func)
    properties: dict[str, dict] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        if pname == "self":
            continue
        json_type = _PY_TO_JSON.get(param.annotation, "string")
        prop: dict[str, Any] = {"type": json_type}
        if pname in descriptions:
            prop["description"] = descriptions[pname]
        properties[pname] = prop
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def skill(
    description: str,
    destructive: bool = False,
    params: dict[str, str] | None = None,
):
    """Decorator that registers a function as a callable skill.

    `description` is shown to the brain so it knows when to use the skill.
    `params` maps argument names to human descriptions (optional but helpful).
    `destructive=True` routes the call through the confirmation gate.
    """

    def decorator(func: Callable) -> Callable:
        _SKILLS[func.__name__] = Skill(
            name=func.__name__,
            func=func,
            description=description,
            parameters=_build_parameters(func, params or {}),
            destructive=destructive,
        )
        return func

    return decorator


def all_skills() -> list[Skill]:
    return list(_SKILLS.values())


def get(name: str) -> Skill | None:
    return _SKILLS.get(name)


def execute_skill(name: str, args: dict) -> Any:
    """Run a skill by name, applying the confirmation gate first.

    Always returns a JSON-serializable value (never raises) so the brain can
    read the outcome — success, decline, or error — and react accordingly.
    """
    sk = _SKILLS.get(name)
    if sk is None:
        return f"Error: no skill named '{name}'."

    if sk.destructive and config.CONFIRM_DESTRUCTIVE:
        if not confirm_action(name, args):
            safety.log_action(name, args, "DECLINED by user")
            return "The user declined to perform this action."

    try:
        result = sk.func(**args)
    except TypeError as exc:
        safety.log_action(name, args, f"BAD ARGS: {exc}")
        return f"Error: wrong arguments for {name}: {exc}"
    except Exception as exc:  # noqa: BLE001 - report everything back to the brain
        safety.log_action(name, args, f"ERROR: {exc}")
        return f"Error while running {name}: {exc}"

    safety.log_action(name, args, result)
    return result if result is not None else "Done."
