"""Optional spoken output via pyttsx3 (offline text-to-speech).

Imported lazily so the assistant still runs if the TTS engine isn't installed.
"""
from __future__ import annotations

_engine = None
_failed = False


def _get_engine():
    global _engine, _failed
    if _engine is not None or _failed:
        return _engine
    try:
        import pyttsx3

        _engine = pyttsx3.init()
    except Exception as exc:  # noqa: BLE001
        _failed = True
        print(f"[voice output unavailable: {exc}]")
    return _engine


def speak(text: str) -> None:
    """Speak `text` aloud. Silently no-ops if TTS isn't available."""
    engine = _get_engine()
    if engine is None:
        return
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as exc:  # noqa: BLE001
        print(f"[voice output error: {exc}]")
