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
# Which brain to use
# ---------------------------------------------------------------------------
# "ollama" = a local model on your own PC. Free forever, offline, unlimited,
# no API key, no daily cap. Recommended.
# "gemini" = Google's cloud API. Smarter, but the free tier has a small
# daily request cap and needs internet.
BRAIN: str = os.getenv("BRAIN", "ollama").strip().lower()


# ---------------------------------------------------------------------------
# Ollama (local brain — no key, no limits)
# ---------------------------------------------------------------------------
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
# Must be a model that supports tool calling. Good 8 GB-VRAM choices:
#   qwen2.5:7b        (balanced; default)
#   qwen2.5:14b       (better, may spill to CPU/RAM on 8 GB VRAM)
#   llama3.1:8b       (also fine at tool calling)
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip()
# Lower = more predictable tool calls. 0.2 is a good assistant default.
OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

# ---------------------------------------------------------------------------
# Gemini (the optional cloud brain)
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
# Flash models are fast, free-tier friendly, and good at tool-calling.
# Each model has its OWN free-tier daily quota, so switching models buys more
# requests. gemini-3.6-flash measured fastest for tool-calling in our tests.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
# Gemini 3.x "thinks" before replying, which adds several seconds of latency.
# 0 = no thinking (fastest, best for simple PC commands). Raise it (e.g. 512)
# for harder multi-step reasoning. -1 = don't send the setting at all (for
# models that don't support it).
GEMINI_THINKING_BUDGET: int = int(os.getenv("GEMINI_THINKING_BUDGET", "0"))

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
# faster-whisper speech-to-text. The ".en" models are English-only: faster AND
# more accurate for English commands (no language guessing). tiny.en is fastest
# but less accurate; base.en is the sweet spot; small.en is more accurate, slower.
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base.en").strip()
# ctranslate2 compute type: int8 (light/fast) | int8_float32 | float32 (slow).
WHISPER_COMPUTE: str = os.getenv("WHISPER_COMPUTE", "int8").strip()
# CPU threads for transcription; 0 = auto (all logical cores).
WHISPER_THREADS: int = int(os.getenv("WHISPER_THREADS", "0"))
# Whisper decoding: 1 = greedy (fastest). Higher = slower, marginally better.
WHISPER_BEAM: int = int(os.getenv("WHISPER_BEAM", "1"))
# Wake phrase for hands-free mode (python main.py --wake). Matching is lenient:
# the last word alone (e.g. "darling") will also trigger it.
WAKE_WORD: str = os.getenv("WAKE_WORD", "hey darling").strip()
# How long a pause (seconds) ends a spoken command in voice/wake mode.
SILENCE_DURATION: float = float(os.getenv("SILENCE_DURATION", "0.8"))
# Mic loudness below which input counts as silence (tune if it cuts you off).
SILENCE_THRESHOLD: float = float(os.getenv("SILENCE_THRESHOLD", "0.015"))

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
