from __future__ import annotations

import subprocess
from pathlib import Path

BLOCKED_COMMAND_FRAGMENTS = (
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "> /dev/",
)
MAX_OUTPUT_CHARS = 50000


def run_bash(workspace: Path, command: str, timeout: int = 120) -> str:
    if any(fragment in command for fragment in BLOCKED_COMMAND_FRAGMENTS):
        return "Error: Dangerous command blocked"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout}s)"

    output = (result.stdout + result.stderr).strip()
    return output[:MAX_OUTPUT_CHARS] if output else "(no output)"
