"""System skills: info, date/time, volume, lock, shutdown, shell commands."""
from __future__ import annotations

import ctypes
import datetime as _dt
import platform
import subprocess

import psutil
import pyautogui

from assistant.registry import skill


@skill("Report CPU, memory, disk, and battery status.")
def system_info() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "memory_percent": vm.percent,
        "memory_used_gb": round(vm.used / 1e9, 2),
        "memory_total_gb": round(vm.total / 1e9, 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / 1e9, 2),
    }
    battery = psutil.sensors_battery()
    if battery is not None:
        info["battery_percent"] = battery.percent
        info["battery_plugged_in"] = battery.power_plugged
    return info


@skill("Get the current local date and time.")
def get_datetime() -> dict:
    now = _dt.datetime.now()
    return {
        "iso": now.isoformat(timespec="seconds"),
        "readable": now.strftime("%A, %d %B %Y, %I:%M %p"),
    }


@skill("Turn the system volume up.", params={"times": "How many steps to raise."})
def volume_up(times: int = 5) -> str:
    for _ in range(max(1, times)):
        pyautogui.press("volumeup")
    return f"Volume up x{times}."


@skill("Turn the system volume down.", params={"times": "How many steps to lower."})
def volume_down(times: int = 5) -> str:
    for _ in range(max(1, times)):
        pyautogui.press("volumedown")
    return f"Volume down x{times}."


@skill("Toggle mute on/off.")
def toggle_mute() -> str:
    pyautogui.press("volumemute")
    return "Toggled mute."


@skill("Lock the Windows session (does not close any apps).")
def lock_screen() -> str:
    ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
    return "Locked the workstation."


@skill(
    "Shut down or restart the PC after a delay. Use cancel_shutdown to abort.",
    destructive=True,
    params={
        "mode": "'shutdown' or 'restart'.",
        "delay_seconds": "Seconds to wait before it happens (gives time to cancel).",
    },
)
def shutdown(mode: str = "shutdown", delay_seconds: int = 30) -> str:
    flag = "/r" if mode.lower().startswith("r") else "/s"
    subprocess.run(["shutdown", flag, "/t", str(delay_seconds)], check=False)
    return f"System will {mode} in {delay_seconds}s. Use cancel_shutdown to abort."


@skill("Cancel a pending shutdown or restart.")
def cancel_shutdown() -> str:
    subprocess.run(["shutdown", "/a"], check=False)
    return "Cancelled any pending shutdown."


@skill(
    "Run a shell command and return its output. Powerful and potentially "
    "dangerous, so it is always confirmed first.",
    destructive=True,
    params={"command": "The command line to execute.", "timeout": "Seconds before giving up."},
)
def run_shell_command(command: str, timeout: int = 60) -> dict:
    proc = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-5000:],
        "stderr": proc.stderr[-5000:],
    }
