from __future__ import annotations

import os
import subprocess
from pathlib import Path


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class CommandFailed(RuntimeError):
    pass


def run(command: str, cwd: Path, timeout: int = 600) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise CommandFailed(f"command failed ({completed.returncode}): {command}\n{output[-6000:]}")
    return output[-12000:]
