from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
FACTORY_ROOT = Path(__file__).resolve().parents[2]


class CommandFailed(RuntimeError):
    pass


def _candidate_executables(name: str) -> list[Path]:
    candidates: list[Path] = []
    discovered = shutil.which(name)
    if discovered:
        candidates.append(Path(discovered))

    if name == "python":
        candidates.insert(0, Path(sys.executable))
    elif name == "rojo":
        candidates.insert(0, FACTORY_ROOT / "tools" / "bin" / ("rojo.exe" if os.name == "nt" else "rojo"))
    elif name == "git" and os.name == "nt":
        candidates.extend(
            [
                Path(r"C:\Program Files\Git\cmd\git.exe"),
                Path(r"C:\Program Files\Git\bin\git.exe"),
                Path.home() / "AppData" / "Local" / "Programs" / "Git" / "cmd" / "git.exe",
            ]
        )
    return candidates


def resolve_executable(name: str) -> Path | None:
    for candidate in _candidate_executables(name):
        if candidate.exists():
            return candidate
    return None


def normalize_command(command: str) -> str:
    stripped = command.lstrip()
    prefix_len = len(command) - len(stripped)
    for name in ("git", "rojo", "python"):
        if stripped == name or stripped.startswith(name + " "):
            executable = resolve_executable(name)
            if executable is None:
                return command
            suffix = stripped[len(name):]
            return command[:prefix_len] + f'"{executable}"' + suffix
    return command


def run(command: str, cwd: Path, timeout: int = 600) -> str:
    resolved = normalize_command(command)
    completed = subprocess.run(
        resolved,
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
