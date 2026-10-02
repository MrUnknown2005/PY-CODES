"""Application & window skills: launch apps, close them, and manage windows."""
from __future__ import annotations

import subprocess

import psutil

from assistant.registry import skill


@skill(
    "Launch an application by name or path, e.g. 'notepad', 'calc', 'chrome', "
    "or a full path to an .exe.",
    params={"name": "Application name or executable path."},
)
def open_app(name: str) -> str:
    # `start` resolves registered app names (notepad, calc, chrome, ...) and paths.
    subprocess.Popen(f'start "" "{name}"', shell=True)
    return f"Launched {name}"


@skill(
    "Close/terminate all running processes whose name matches (e.g. 'notepad'). "
    "This can discard unsaved work.",
    destructive=True,
    params={"name": "Process/app name to close, with or without .exe."},
)
def close_app(name: str) -> str:
    needle = name.lower().removesuffix(".exe")
    killed = 0
    for proc in psutil.process_iter(["name"]):
        pname = (proc.info.get("name") or "").lower().removesuffix(".exe")
        if pname == needle:
            try:
                proc.terminate()
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return f"Closed {killed} process(es) matching '{name}'."


@skill("List the titles of all currently open windows.")
def list_windows() -> dict:
    import pygetwindow as gw

    titles = [t for t in gw.getAllTitles() if t.strip()]
    return {"windows": titles}


@skill(
    "Bring a window to the front by (part of) its title.",
    params={"title": "Any text contained in the target window's title."},
)
def focus_window(title: str) -> str:
    import pygetwindow as gw

    matches = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
    if not matches:
        return f"No open window with title containing '{title}'."
    win = matches[0]
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
    except Exception as exc:  # noqa: BLE001
        return f"Found '{win.title}' but could not focus it: {exc}"
    return f"Focused window: {win.title}"


@skill(
    "List running processes (name + memory), most memory-hungry first.",
    params={"limit": "How many processes to return."},
)
def list_processes(limit: int = 15) -> dict:
    procs = []
    for proc in psutil.process_iter(["name", "memory_info"]):
        mem = getattr(proc.info.get("memory_info"), "rss", 0) or 0
        procs.append({"name": proc.info.get("name"), "memory_mb": round(mem / 1e6, 1)})
    procs.sort(key=lambda p: p["memory_mb"], reverse=True)
    return {"processes": procs[:limit]}
