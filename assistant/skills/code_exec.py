"""The 'do anything' escape hatch.

When no predefined skill fits, the brain can write a short Python script and run
it here. This is intentionally the most powerful — and most dangerous — skill,
so it is always `destructive` (confirmed) and the code is shown before running.

The script runs in a separate Python process with a timeout, so a hang or crash
can't take the assistant down with it.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile

from assistant.registry import skill


@skill(
    "Run a short Python 3 script to accomplish a task that no other skill covers. "
    "The script's printed output is returned. Prefer dedicated skills when one fits; "
    "use this only as a fallback. The user will see and approve the code first.",
    destructive=True,
    params={
        "code": "The Python source to execute.",
        "timeout": "Maximum seconds to let it run.",
    },
)
def run_python(code: str, timeout: int = 60) -> dict:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        script_path = tmp.name

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Script exceeded the {timeout}s timeout and was stopped."}

    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
    }
