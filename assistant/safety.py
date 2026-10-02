"""Safety helpers: protected-path checks and a simple action log.

These are deliberately conservative. The goal is to make it hard for the
assistant to damage the operating system or silently do something irreversible.
"""
from __future__ import annotations

import logging
import os

import config

# ---------------------------------------------------------------------------
# Action logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("assistant")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    _file = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    _file.setFormatter(_fmt)
    logger.addHandler(_file)


def log_action(name: str, args: dict, result) -> None:
    """Record every skill invocation (name, args, and a short result)."""
    summary = str(result)
    if len(summary) > 500:
        summary = summary[:500] + "…"
    logger.info("skill=%s args=%s -> %s", name, args, summary)


# ---------------------------------------------------------------------------
# Protected paths
# ---------------------------------------------------------------------------
def _normalize(path: str) -> str:
    """Expand ~ and %VARS%, then return an absolute, normalized path."""
    expanded = os.path.expandvars(os.path.expanduser(path))
    return os.path.normcase(os.path.abspath(expanded))


# Folders the assistant must never modify/delete inside.
_PROTECTED_ROOTS = [
    _normalize(os.environ.get("SystemRoot", r"C:\Windows")),
    _normalize(os.environ.get("ProgramFiles", r"C:\Program Files")),
    _normalize(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    _normalize(os.environ.get("ProgramData", r"C:\ProgramData")),
    # The assistant's own source folder.
    _normalize(os.path.dirname(os.path.abspath(__file__))),
]


def is_protected(path: str) -> bool:
    """True if `path` lives inside (or is) a protected system location."""
    target = _normalize(path)
    for root in _PROTECTED_ROOTS:
        if target == root or target.startswith(root + os.sep):
            return True
    # Guard against operating on a drive root like C:\ itself.
    drive, tail = os.path.splitdrive(target)
    if drive and tail in ("", os.sep):
        return True
    return False


def ensure_writable(path: str) -> None:
    """Raise if `path` is a protected location. Call before destructive ops."""
    if is_protected(path):
        raise PermissionError(
            f"Refusing to modify a protected system location: {path}"
        )


def resolve(path: str) -> str:
    """Public helper for skills: expand ~ / %VARS% and make absolute."""
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
