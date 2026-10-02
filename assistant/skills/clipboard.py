"""Clipboard skills: read and write the Windows clipboard."""
from __future__ import annotations

import pyperclip

from assistant.registry import skill


@skill("Read and return the current text on the clipboard.")
def get_clipboard() -> dict:
    return {"text": pyperclip.paste()}


@skill(
    "Copy text onto the clipboard.",
    params={"text": "The text to place on the clipboard."},
)
def set_clipboard(text: str) -> str:
    pyperclip.copy(text)
    return f"Copied {len(text)} characters to the clipboard."
