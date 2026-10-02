"""Console text output helpers (tiny, but keeps formatting in one place)."""
from __future__ import annotations


def say(text: str) -> None:
    print(f"\nMilena: {text}\n")


def info(text: str) -> None:
    print(text)
