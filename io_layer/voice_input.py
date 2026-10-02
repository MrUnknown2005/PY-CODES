"""Optional voice input: microphone capture + faster-whisper transcription.

Three ways to listen, all sharing the same offline transcription:

* ``listen()``              — push-to-talk: record until the user presses Enter.
* ``listen_command()``      — record a single utterance and stop automatically
                              when the speaker goes quiet (silence detection).
* ``listen_for_wake_word()``— keep listening until the wake phrase
                              ("Hey Darling" by default) is heard.

Whichever is used, the result is plain text that goes through the exact same
skill pipeline as a typed command.

All heavy dependencies are imported lazily, so the assistant still runs in
text-only mode if these libraries aren't installed.
"""
from __future__ import annotations

import config

_model = None  # cached WhisperModel instance
_SAMPLE_RATE = 16000


class VoiceUnavailable(RuntimeError):
    """Raised when the voice dependencies can't be loaded."""


def _audio_modules():
    """Import numpy + sounddevice, or raise VoiceUnavailable."""
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as exc:  # noqa: BLE001
        raise VoiceUnavailable(
            f"sounddevice/numpy not available: {exc}. "
            "Install voice extras: pip install -r requirements-voice.txt"
        ) from exc
    return np, sd


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
    # CPU int8 keeps it light; model/compute/threads are configurable.
    threads = config.WHISPER_THREADS or None  # None -> ctranslate2 auto (all cores)
    _model = WhisperModel(
        config.WHISPER_MODEL,
        device="cpu",
        compute_type=config.WHISPER_COMPUTE,
        cpu_threads=threads or 0,
    )
    return _model


def _transcribe(audio) -> str:
    """Run the cached Whisper model over a mono float32 numpy array."""
    model = _get_model()
    segments, _info = model.transcribe(
        audio,
        language="en",
        beam_size=config.WHISPER_BEAM,
        # Only ever one language, so skip the language-detection pass entirely.
        condition_on_previous_text=False,
    )
    return " ".join(seg.text for seg in segments).strip()


def _normalize(text: str) -> str:
    """Lowercase, drop punctuation, and collapse whitespace for matching."""
    cleaned = "".join(c if (c.isalnum() or c.isspace()) else " " for c in text.lower())
    return " ".join(cleaned.split())


def _record_until_silence(
    max_seconds: float = 20.0,
    silence_threshold: float | None = None,
    silence_duration: float | None = None,
    start_timeout: float = 8.0,
):
    """Record one utterance, stopping after a stretch of silence.

    Returns a mono float32 numpy array, or None if nobody spoke before
    ``start_timeout`` elapsed. Raises VoiceUnavailable if audio can't load.

    The silence threshold/duration default to the settings in config.py.
    """
    if silence_threshold is None:
        silence_threshold = config.SILENCE_THRESHOLD
    if silence_duration is None:
        silence_duration = config.SILENCE_DURATION
    np, sd = _audio_modules()

    block_dur = 0.1
    block_size = int(_SAMPLE_RATE * block_dur)
    blocks: list = []
    started = False
    silent_for = 0.0
    waited = 0.0

    with sd.InputStream(
        samplerate=_SAMPLE_RATE, channels=1, dtype="float32", blocksize=block_size
    ) as stream:
        while True:
            data, _overflowed = stream.read(block_size)
            rms = float(np.sqrt(np.mean(np.square(data))))

            if not started:
                if rms >= silence_threshold:
                    started = True
                    blocks.append(data.copy())
                else:
                    waited += block_dur
                    if waited >= start_timeout:
                        return None
                continue

            blocks.append(data.copy())
            if rms < silence_threshold:
                silent_for += block_dur
                if silent_for >= silence_duration:
                    break
            else:
                silent_for = 0.0

            if len(blocks) * block_dur >= max_seconds:
                break

    if not blocks:
        return None
    return np.concatenate(blocks, axis=0).flatten()


def listen() -> str:
    """Record until the user presses Enter, then return the transcribed text.

    Raises VoiceUnavailable if the audio/transcription stack can't be loaded.
    """
    np, sd = _audio_modules()
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
    text = _transcribe(audio)
    if text:
        print(f"🗣  You said: {text}")
    return text


def listen_command(max_seconds: float = 20.0) -> str:
    """Record a single spoken command, auto-stopping on silence.

    Returns the transcribed text (empty string if nothing was heard).
    Raises VoiceUnavailable if the audio/transcription stack can't be loaded.
    """
    _get_model()  # validate the stack up front
    print("🎙  Listening… (speak, then pause)")
    audio = _record_until_silence(max_seconds=max_seconds)
    if audio is None or len(audio) == 0:
        return ""
    text = _transcribe(audio)
    if text:
        print(f"🗣  You said: {text}")
    return text


def listen_for_wake_word(wake_word: str | None = None) -> bool:
    """Block until the wake phrase is heard, then return True.

    Matching is lenient: the full phrase ("hey darling") OR just its last word
    ("darling") anywhere in a heard utterance counts. Silence is skipped
    without transcription to keep CPU use low. Raises VoiceUnavailable if the
    audio/transcription stack can't be loaded; let KeyboardInterrupt propagate
    to stop listening.
    """
    phrase = _normalize(wake_word or config.WAKE_WORD)
    last_word = phrase.split()[-1] if phrase else ""
    _get_model()  # validate / warm up the stack

    while True:
        audio = _record_until_silence(
            max_seconds=4.0, silence_duration=0.6, start_timeout=3600.0
        )
        if audio is None or len(audio) == 0:
            continue
        heard = _normalize(_transcribe(audio))
        if not heard:
            continue
        if (phrase and phrase in heard) or (last_word and last_word in heard.split()):
            return True
        # Heard speech, but not the wake word — keep waiting.
