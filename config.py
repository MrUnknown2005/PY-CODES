"""Central configuration for the assistant.

Everything tunable lives here. Secrets (your API key) come from a local `.env`
file that is NOT committed to git. Copy `.env.example` to `.env` and fill it in.
"""
from __future__ import annotations

import os
import platform

from dotenv import load_dotenv

# Load variables from a local .env file (if present) into the environment.
load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "y")


# ---------------------------------------------------------------------------
# Gemini (the "brain")
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
# Flash models are fast, free-tier friendly, and good at tool-calling.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
# When True, any skill marked `destructive` asks for confirmation before running.
CONFIRM_DESTRUCTIVE: bool = _as_bool(os.getenv("CONFIRM_DESTRUCTIVE"), True)
# Hard cap on how many tool-call rounds the brain may take for one request.
MAX_STEPS: int = int(os.getenv("MAX_STEPS", "10"))

# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------
# Speak replies aloud (needs the optional voice extras installed).
VOICE_OUTPUT: bool = _as_bool(os.getenv("VOICE_OUTPUT"), False)
# faster-whisper model size for speech-to-text: tiny | base | small | medium | large-v3
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base").strip()
# Wake phrase for hands-free mode (python main.py --wake). Matching is lenient:
# the last word alone (e.g. "darling") will also trigger it.
WAKE_WORD: str = os.getenv("WAKE_WORD", "hey darling").strip()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE: str = os.getenv("LOG_FILE", "assistant.log").strip()


# ---------------------------------------------------------------------------
# Useful filesystem locations (handed to the brain so it can build real paths)
# ---------------------------------------------------------------------------
USER_HOME: str = os.path.expanduser("~")


def _known_folder(name: str) -> str:
    """Return a well-known user folder, accounting for OneDrive redirection."""
    plain = os.path.join(USER_HOME, name)
    if os.path.isdir(plain):
        return plain
    onedrive = os.path.join(USER_HOME, "OneDrive", name)
    if os.path.isdir(onedrive):
        return onedrive
    return plain  # fall back to the plain path even if it doesn't exist yet


DESKTOP: str = _known_folder("Desktop")
DOCUMENTS: str = _known_folder("Documents")
DOWNLOADS: str = _known_folder("Downloads")


def environment_summary() -> str:
    """A short description of the machine, injected into the system prompt."""
    return (
        f"Operating system: {platform.system()} {platform.release()}\n"
        f"User home: {USER_HOME}\n"
        f"Desktop: {DESKTOP}\n"
        f"Documents: {DOCUMENTS}\n"
        f"Downloads: {DOWNLOADS}\n"
        f"Current working directory: {os.getcwd()}"
    )
