"""Importing this package registers every built-in skill.

Each submodule uses the @skill decorator, which adds entries to the registry at
import time. If an optional dependency for one group is missing, that group is
skipped with a warning instead of crashing the whole assistant.
"""
from __future__ import annotations

import importlib
import warnings

# Order doesn't matter; every module just registers its skills on import.
_SKILL_MODULES = [
    "assistant.skills.files",
    "assistant.skills.apps",
    "assistant.skills.input_control",
    "assistant.skills.screen",
    "assistant.skills.system",
    "assistant.skills.web",
    "assistant.skills.clipboard",
    "assistant.skills.code_exec",
]

for _mod in _SKILL_MODULES:
    try:
        importlib.import_module(_mod)
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"Skill module '{_mod}' could not be loaded: {exc}")
