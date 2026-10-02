"""Optional voice input: push-to-talk recording + faster-whisper transcription.

Usage pattern (see main.py): the user presses Enter on an empty prompt to start
talking, speaks, then presses Enter again to stop. The recorded audio is
transcribed locally (offline) with faster-whisper and returned as text, which
then goes through the exact same skill pipeline as typed commands.

All heavy dependencies are imported lazily, so the assistant runs fine in
text-only mode if these libraries aren't installed (e.g. on a Python version
without prebuilt wheels yet).
"""
from __future__ import annotations

import config

_model = None  # cached WhisperModel instance
_SAMPLE_RATE = 16000


class VoiceUnavailable(RuntimeError):
    """Raised when the voice dependencies can't be loaded."""


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # noqa: BLE001
        raise VoiceUnavailable(
            f"faster-whisper not available: {exc}. "
            "Install voice extras: pip install -r requirements-voice.txt"
        ) from exc
    # CPU int8 keeps it light; adjust in config via WHISPER_MODEL.
    _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def listen() -> str:
    """Record until the user presses Enter, then return the transcribed text.

    Raises VoiceUnavailable if the audio/transcription stack can't be loaded.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as exc:  # noqa: BLE001
        raise VoiceUnavailable(
            f"sounddevice/numpy not available: {exc}. "
            "Install voice extras: pip install -r requirements-voice.txt"
        ) from exc

    model = _get_model()  # may raise VoiceUnavailable

    frames: list = []

    def _callback(indata, _frames, _time, _status):
        frames.append(indata.copy())

    print("🎙  Recording… press Enter to stop.")
    with sd.InputStream(
        samplerate=_SAMPLE_RATE, channels=1, dtype="float32", callback=_callback
    ):
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

    if not frames:
        return ""

    audio = np.concatenate(frames, axis=0).flatten()
    segments, _info = model.transcribe(audio, language="en")
    text = " ".join(seg.text for seg in segments).strip()
    if text:
        print(f"🗣  You said: {text}")
    return text
