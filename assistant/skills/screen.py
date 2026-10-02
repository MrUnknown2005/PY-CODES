"""Screen skills: take screenshots and locate an image on screen."""
from __future__ import annotations

import os
import time

import pyautogui

from assistant import safety
from assistant.registry import skill


@skill(
    "Take a screenshot of the whole screen and save it to a PNG file. "
    "Returns the saved path.",
    params={"path": "Where to save the PNG. Defaults to a timestamped file in ./screenshots."},
)
def screenshot(path: str = "") -> dict:
    if not path:
        folder = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"screen_{int(time.time())}.png")
    full = safety.resolve(path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    img = pyautogui.screenshot()
    img.save(full)
    return {"path": full, "size": list(img.size)}


@skill(
    "Find where a template image appears on the current screen. "
    "Returns the center coordinates, or an error if it isn't found.",
    params={
        "image_path": "Path to a small PNG to look for on screen.",
        "confidence": "Match confidence 0-1 (needs opencv; ignored if unavailable).",
    },
)
def locate_on_screen(image_path: str, confidence: float = 0.8) -> dict:
    full = safety.resolve(image_path)
    if not os.path.isfile(full):
        return {"error": f"Image not found: {full}"}
    try:
        box = pyautogui.locateOnScreen(full, confidence=confidence)
    except TypeError:
        # opencv not installed -> confidence unsupported; try exact match.
        box = pyautogui.locateOnScreen(full)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Lookup failed: {exc}"}
    if box is None:
        return {"found": False}
    center = pyautogui.center(box)
    return {"found": True, "x": center.x, "y": center.y}
