"""Mouse and keyboard control, backed by pyautogui.

pyautogui's fail-safe is enabled: slam the mouse into any screen corner to
abort an in-progress automation immediately.
"""
from __future__ import annotations

import pyautogui

from assistant.registry import skill

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # small gap between actions so the UI can keep up


@skill("Get the current (x, y) position of the mouse cursor.")
def get_mouse_position() -> dict:
    x, y = pyautogui.position()
    return {"x": x, "y": y}


@skill("Get the screen resolution in pixels.")
def get_screen_size() -> dict:
    w, h = pyautogui.size()
    return {"width": w, "height": h}


@skill(
    "Move the mouse cursor to absolute screen coordinates.",
    params={
        "x": "X pixel coordinate.",
        "y": "Y pixel coordinate.",
        "duration": "Seconds the movement should take (for a smooth glide).",
    },
)
def move_mouse(x: int, y: int, duration: float = 0.25) -> str:
    pyautogui.moveTo(x, y, duration=duration)
    return f"Moved mouse to ({x}, {y})."


@skill(
    "Click the mouse. If x and y are given, move there first; otherwise click "
    "wherever the cursor is.",
    params={
        "x": "Optional X coordinate.",
        "y": "Optional Y coordinate.",
        "button": "'left', 'right', or 'middle'.",
        "clicks": "Number of clicks (2 = double-click).",
    },
)
def click(x: int = -1, y: int = -1, button: str = "left", clicks: int = 1) -> str:
    kwargs = {"button": button, "clicks": clicks, "interval": 0.1}
    if x >= 0 and y >= 0:
        kwargs.update({"x": x, "y": y})
    pyautogui.click(**kwargs)
    return f"Clicked ({button} x{clicks})."


@skill(
    "Drag the mouse from one point to another (press, move, release).",
    params={"x1": "Start X.", "y1": "Start Y.", "x2": "End X.", "y2": "End Y."},
)
def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.4) -> str:
    pyautogui.moveTo(x1, y1)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    return f"Dragged from ({x1}, {y1}) to ({x2}, {y2})."


@skill(
    "Scroll the mouse wheel. Positive scrolls up, negative scrolls down.",
    params={"amount": "Scroll amount in 'clicks' (e.g. 500 or -500)."},
)
def scroll(amount: int) -> str:
    pyautogui.scroll(amount)
    return f"Scrolled {amount}."


@skill(
    "Type a string of text at the current focus, as if typed on the keyboard.",
    params={"text": "The text to type.", "interval": "Seconds between keystrokes."},
)
def type_text(text: str, interval: float = 0.02) -> str:
    pyautogui.write(text, interval=interval)
    return f"Typed {len(text)} characters."


@skill(
    "Press a single key, e.g. 'enter', 'esc', 'tab', 'f5', 'up', 'delete'.",
    params={"key": "Key name understood by pyautogui."},
)
def press_key(key: str) -> str:
    pyautogui.press(key)
    return f"Pressed '{key}'."


@skill(
    "Press a keyboard shortcut / chord. Give the keys comma-separated, "
    "e.g. 'ctrl,c' or 'alt,tab' or 'ctrl,shift,esc'.",
    params={"keys": "Comma-separated key names pressed together."},
)
def hotkey(keys: str) -> str:
    parts = [k.strip() for k in keys.split(",") if k.strip()]
    if not parts:
        return "No keys given."
    pyautogui.hotkey(*parts)
    return f"Pressed hotkey: {'+'.join(parts)}"
