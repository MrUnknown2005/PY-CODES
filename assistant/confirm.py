"""The confirmation gate shown before any destructive action."""
from __future__ import annotations


def _format_args(args: dict) -> str:
    lines = []
    for key, value in args.items():
        text = str(value)
        if "\n" in text or len(text) > 80:
            # Show long / multi-line values (e.g. generated code) in a block.
            lines.append(f"  {key}:")
            for line in text.splitlines() or [""]:
                lines.append(f"    | {line}")
        else:
            lines.append(f"  {key}: {text}")
    return "\n".join(lines) if lines else "  (no arguments)"


def confirm_action(name: str, args: dict, note: str = "") -> bool:
    """Ask the user to approve a destructive action. Returns True if approved.

    Defaults to NO on an empty answer, so a stray Enter never deletes anything.
    """
    print("\n" + "=" * 60)
    print("  CONFIRMATION REQUIRED  (this action may be irreversible)")
    print("=" * 60)
    print(f"Action: {name}")
    print(_format_args(args))
    if note:
        print(f"\nNote: {note}")
    try:
        answer = input("\nProceed? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")
