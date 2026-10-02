"""File-system skills: list, read, write, move, copy, delete, search, open.

Destructive operations check the protected-path denylist and, for deletes,
use the Recycle Bin by default so mistakes are recoverable.
"""
from __future__ import annotations

import fnmatch
import os
import shutil

from assistant import safety
from assistant.registry import skill


@skill(
    "List the files and folders inside a directory.",
    params={"path": "Folder to list. Defaults to the current directory."},
)
def list_directory(path: str = ".") -> dict:
    full = safety.resolve(path)
    if not os.path.isdir(full):
        return {"error": f"Not a directory: {full}"}
    entries = []
    for name in sorted(os.listdir(full)):
        p = os.path.join(full, name)
        entries.append({"name": name, "is_dir": os.path.isdir(p)})
    return {"path": full, "entries": entries}


@skill(
    "Read and return the text contents of a file.",
    params={
        "path": "File to read.",
        "max_chars": "Maximum characters to return (file is truncated beyond this).",
    },
)
def read_file(path: str, max_chars: int = 20000) -> dict:
    full = safety.resolve(path)
    if not os.path.isfile(full):
        return {"error": f"Not a file: {full}"}
    with open(full, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read(max_chars + 1)
    truncated = len(text) > max_chars
    return {"path": full, "content": text[:max_chars], "truncated": truncated}


@skill(
    "Create a new text file or overwrite an existing one with the given content.",
    destructive=True,
    params={"path": "File to write.", "content": "Text to write into the file."},
)
def write_file(path: str, content: str = "") -> str:
    full = safety.resolve(path)
    safety.ensure_writable(full)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"Wrote {len(content)} characters to {full}"


@skill(
    "Append text to the end of a file (creating it if needed).",
    params={"path": "File to append to.", "content": "Text to append."},
)
def append_file(path: str, content: str) -> str:
    full = safety.resolve(path)
    safety.ensure_writable(full)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "a", encoding="utf-8") as fh:
        fh.write(content)
    return f"Appended {len(content)} characters to {full}"


@skill(
    "Create a new (possibly nested) folder.",
    params={"path": "Folder path to create."},
)
def create_directory(path: str) -> str:
    full = safety.resolve(path)
    safety.ensure_writable(full)
    os.makedirs(full, exist_ok=True)
    return f"Created directory {full}"


@skill(
    "Move or rename a file or folder.",
    destructive=True,
    params={"source": "Existing path.", "destination": "New path."},
)
def move_file(source: str, destination: str) -> str:
    src = safety.resolve(source)
    dst = safety.resolve(destination)
    safety.ensure_writable(src)
    safety.ensure_writable(dst)
    if not os.path.exists(src):
        return f"Source does not exist: {src}"
    shutil.move(src, dst)
    return f"Moved {src} -> {dst}"


@skill(
    "Copy a file or folder to a new location.",
    destructive=True,
    params={"source": "Existing path.", "destination": "Destination path."},
)
def copy_file(source: str, destination: str) -> str:
    src = safety.resolve(source)
    dst = safety.resolve(destination)
    safety.ensure_writable(dst)
    if not os.path.exists(src):
        return f"Source does not exist: {src}"
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(src, dst)
    return f"Copied {src} -> {dst}"


@skill(
    "Delete a file or folder. By default it goes to the Recycle Bin (recoverable). "
    "Set permanent=True only when the user explicitly wants it gone for good.",
    destructive=True,
    params={
        "path": "File or folder to delete.",
        "permanent": "If true, delete permanently instead of using the Recycle Bin.",
    },
)
def delete_file(path: str, permanent: bool = False) -> str:
    full = safety.resolve(path)
    safety.ensure_writable(full)
    if not os.path.exists(full):
        return f"Nothing to delete: {full}"

    if permanent:
        if os.path.isdir(full):
            shutil.rmtree(full)
        else:
            os.remove(full)
        return f"Permanently deleted {full}"

    # Default: send to the Recycle Bin so it can be restored.
    try:
        from send2trash import send2trash
    except ImportError:
        return (
            "send2trash is not installed, so I can't use the Recycle Bin. "
            "Install it (pip install send2trash) or re-issue with permanent=True."
        )
    send2trash(full)
    return f"Sent {full} to the Recycle Bin"


@skill(
    "Search for files matching a wildcard pattern under a folder.",
    params={
        "root": "Folder to search from.",
        "pattern": "Wildcard like *.txt or report_*.pdf.",
        "max_results": "Maximum number of matches to return.",
    },
)
def search_files(root: str, pattern: str, max_results: int = 100) -> dict:
    base = safety.resolve(root)
    matches: list[str] = []
    for dirpath, _dirs, files in os.walk(base):
        for fname in files:
            if fnmatch.fnmatch(fname.lower(), pattern.lower()):
                matches.append(os.path.join(dirpath, fname))
                if len(matches) >= max_results:
                    return {"matches": matches, "truncated": True}
    return {"matches": matches, "truncated": False}


@skill(
    "Open a file with its default application (as if double-clicked).",
    params={"path": "File to open."},
)
def open_file(path: str) -> str:
    full = safety.resolve(path)
    if not os.path.exists(full):
        return f"File does not exist: {full}"
    os.startfile(full)  # type: ignore[attr-defined]  # Windows-only
    return f"Opened {full}"
