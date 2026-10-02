"""The Brain interface.

A Brain turns a line of natural-language input into actions (by calling skills)
and returns a text reply. Keeping this interface tiny is what lets us swap
Gemini for a local model (Ollama) or Claude later without touching any skill.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Brain(ABC):
    @abstractmethod
    def ask(self, user_text: str) -> str:
        """Handle one user request and return the assistant's text reply."""
        raise NotImplementedError

    def reset(self) -> None:
        """Clear any conversation memory. Optional for subclasses to override."""
