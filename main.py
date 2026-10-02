"""Jarvis-style PC assistant — entry point.

Run it:
    python main.py              # type your commands
    python main.py --voice      # press Enter on an empty line to speak a command
    python main.py --speak      # read replies aloud (text input)
    python main.py --voice --speak   # full hands-light mode
    python main.py --wake       # hands-free: say "Hey Darling", then your command

Type 'exit' (or press Ctrl+C) to quit. Type 'reset' to clear the conversation.
"""
from __future__ import annotations

import argparse
import sys

import config
import assistant.skills  # noqa: F401  -- importing registers all skills
from assistant import registry
from io_layer import text_io, voice_output

BANNER = r"""
   ___                  _
  |_  |                (_)
    | | __ _ _ ____   ___ ___
    | |/ _` | '__\ \ / / / __|
/\__/ / (_| | |   \ V /| \__ \
\____/ \__,_|_|    \_/ |_|___/   your PC assistant
"""


def _check_setup() -> bool:
    if config.BRAIN == "ollama":
        return True  # local brain needs no key; it reports its own errors
    if not config.GEMINI_API_KEY:
        print(
            "\n[setup needed] No Gemini API key found.\n"
            "  1. Get a free key: https://aistudio.google.com/apikey\n"
            "  2. Copy .env.example to .env\n"
            "  3. Put your key in it:  GEMINI_API_KEY=your_key_here\n"
        )
        return False
    return True


def build_brain():
    """Create the brain selected by BRAIN in .env."""
    if config.BRAIN == "gemini":
        from assistant.brain.gemini_brain import GeminiBrain

        return GeminiBrain(), f"Gemini ({config.GEMINI_MODEL})"
    if config.BRAIN == "ollama":
        from assistant.brain.ollama_brain import OllamaBrain

        return OllamaBrain(), f"local ({config.OLLAMA_MODEL})"
    raise RuntimeError(
        f"Unknown BRAIN '{config.BRAIN}' in .env — use 'ollama' or 'gemini'."
    )


def _get_command(voice_mode: bool) -> str | None:
    """Return the next user command, or None to quit. Handles voice vs text."""
    try:
        typed = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not voice_mode:
        return typed

    # Voice mode: a typed line is used directly; an empty line starts recording.
    if typed:
        return typed
    from io_layer import voice_input

    try:
        return voice_input.listen()
    except voice_input.VoiceUnavailable as exc:
        print(f"[voice unavailable] {exc}\nFalling back to typing for this command.")
        return input("> ").strip()


def _handle(command: str, brain, speak_replies: bool) -> bool:
    """Process one command. Return False if the user asked to quit."""
    if not command:
        return True
    low = command.lower()
    if low in ("exit", "quit", "bye"):
        return False
    if low == "reset":
        brain.reset()
        text_io.info("(conversation cleared)")
        return True

    reply = brain.ask(command)
    text_io.say(reply)
    if speak_replies:
        voice_output.speak(reply)
    return True


def _wake_loop(brain, speak_replies: bool) -> None:
    """Hands-free loop: listen for the wake word, then run the spoken command."""
    from io_layer import voice_input

    print(f'Hands-free mode ON — say "{config.WAKE_WORD}" to wake me.')
    try:
        voice_input._get_model()  # warm up (first run may download the model)
    except voice_input.VoiceUnavailable as exc:
        print(f"[voice unavailable] {exc}")
        return

    try:
        while True:
            voice_input.listen_for_wake_word()
            if speak_replies:
                voice_output.speak("Yes?")
            else:
                text_io.info("— awake, listening for your command…")
            command = voice_input.listen_command()
            if not command:
                text_io.info("(heard nothing — back to sleep)")
                continue
            if not _handle(command, brain, speak_replies):
                break
    except KeyboardInterrupt:
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis-style PC assistant")
    parser.add_argument(
        "--voice", action="store_true", help="enable push-to-talk voice input"
    )
    parser.add_argument(
        "--speak", action="store_true", help="read replies aloud (text-to-speech)"
    )
    parser.add_argument(
        "--wake",
        action="store_true",
        help=f'hands-free: wake on "{config.WAKE_WORD}" (implies --speak)',
    )
    args = parser.parse_args()

    print(BANNER)
    if not _check_setup():
        return 1

    speak_replies = args.speak or args.wake or config.VOICE_OUTPUT

    try:
        brain, brain_label = build_brain()
    except Exception as exc:  # noqa: BLE001
        print(f"[could not start the brain] {exc}")
        return 1

    print(f"Loaded {len(registry.all_skills())} skills. Brain: {brain_label}")
    print(
        "Confirmation for risky actions is "
        + ("ON" if config.CONFIRM_DESTRUCTIVE else "OFF")
        + ". Fail-safe: slam the mouse to a screen corner to abort automation."
    )
    if args.voice:
        print("Voice input ON — press Enter on an empty line to speak.")
    print("Type 'exit' to quit, 'reset' to clear the conversation.\n")

    if args.wake:
        _wake_loop(brain, speak_replies)
        print("\nGoodbye!")
        return 0

    while True:
        command = _get_command(args.voice)
        if command is None:
            break
        if not _handle(command, brain, speak_replies):
            break

    print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
