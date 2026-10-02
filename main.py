"""Jarvis-style PC assistant — entry point.

Run it:
    python main.py              # type your commands
    python main.py --voice      # press Enter on an empty line to speak a command
    python main.py --speak      # read replies aloud (text input)
    python main.py --voice --speak   # full hands-light mode

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
    if not config.GEMINI_API_KEY:
        print(
            "\n[setup needed] No Gemini API key found.\n"
            "  1. Get a free key: https://aistudio.google.com/apikey\n"
            "  2. Copy .env.example to .env\n"
            "  3. Put your key in it:  GEMINI_API_KEY=your_key_here\n"
        )
        return False
    return True


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis-style PC assistant")
    parser.add_argument(
        "--voice", action="store_true", help="enable push-to-talk voice input"
    )
    parser.add_argument(
        "--speak", action="store_true", help="read replies aloud (text-to-speech)"
    )
    args = parser.parse_args()

    print(BANNER)
    if not _check_setup():
        return 1

    speak_replies = args.speak or config.VOICE_OUTPUT

    try:
        from assistant.brain.gemini_brain import GeminiBrain

        brain = GeminiBrain()
    except Exception as exc:  # noqa: BLE001
        print(f"[could not start the brain] {exc}")
        return 1

    print(f"Loaded {len(registry.all_skills())} skills. Model: {config.GEMINI_MODEL}")
    print(
        "Confirmation for risky actions is "
        + ("ON" if config.CONFIRM_DESTRUCTIVE else "OFF")
        + ". Fail-safe: slam the mouse to a screen corner to abort automation."
    )
    if args.voice:
        print("Voice input ON — press Enter on an empty line to speak.")
    print("Type 'exit' to quit, 'reset' to clear the conversation.\n")

    while True:
        command = _get_command(args.voice)
        if command is None:
            break
        if not command:
            continue
        low = command.lower()
        if low in ("exit", "quit", "bye"):
            break
        if low == "reset":
            brain.reset()
            text_io.info("(conversation cleared)")
            continue

        reply = brain.ask(command)
        text_io.say(reply)
        if speak_replies:
            voice_output.speak(reply)

    print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
