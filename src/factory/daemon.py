from __future__ import annotations

import json
import os
import time
import urllib.request
import zipfile
from dataclasses import asdict
from pathlib import Path

from .runner import run_product
from .process import resolve_executable


ROJO_VERSION = "7.6.1"
ROJO_WINDOWS_URL = f"https://github.com/rojo-rbx/rojo/releases/download/v{ROJO_VERSION}/rojo-{ROJO_VERSION}-windows-x86_64.zip"


class FactoryLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0)
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        if os.name == "nt":
            import msvcrt
            self.handle.seek(0)
            try:
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                self.handle.close()
                raise RuntimeError("factory already running") from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle is None:
            return
        if os.name == "nt":
            import msvcrt
            try:
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        self.handle.close()


def ensure_managed_rojo(root: Path) -> dict:
    existing = resolve_executable("rojo")
    if existing is not None:
        return {"ok": True, "action": "existing", "path": str(existing)}

    if os.name != "nt":
        return {"ok": False, "action": "manual", "reason": "managed bootstrap currently targets Windows"}

    tools = root / "tools"
    bin_dir = tools / "bin"
    archive = tools / f"rojo-{ROJO_VERSION}-windows-x86_64.zip"
    bin_dir.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(ROJO_WINDOWS_URL, archive)
    with zipfile.ZipFile(archive) as payload:
        payload.extractall(bin_dir)
    rojo = bin_dir / "rojo.exe"
    if not rojo.exists() or rojo.stat().st_size < 1_000_000:
        return {"ok": False, "action": "bootstrap_failed", "reason": "rojo.exe not extracted or unexpectedly small"}
    return {"ok": True, "action": "bootstrapped", "path": str(rojo), "bytes": rojo.stat().st_size}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def run_once(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parents[2]
    state_root = root / "state"
    work_root = root / "work" / "repos"
    started = time.time()

    tooling = {"rojo": ensure_managed_rojo(root)}
    if not tooling["rojo"]["ok"]:
        summary = {
            "state": "BLOCKED_TOOLING",
            "started_at_unix": started,
            "finished_at_unix": time.time(),
            "tooling": tooling,
            "products": [],
        }
        _write_json(state_root / "factory-last-run.json", summary)
        return summary

    manifests = sorted((root / "products").glob("*.toml"))
    results = [run_product(manifest, work_root, state_root) for manifest in manifests]
    product_states = [item.state for item in results]
    if any(state.startswith("QUARANTINED") for state in product_states):
        overall = "DEGRADED"
    elif all(state == "PUBLISHED" for state in product_states):
        overall = "PUBLISHED_ALL"
    elif any(state.startswith("READY_WAITING") for state in product_states):
        overall = "WAITING_PLATFORM_GATE"
    else:
        overall = "HEALTHY"

    summary = {
        "state": overall,
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "duration_seconds": round(time.time() - started, 3),
        "tooling": tooling,
        "products": [asdict(item) for item in results],
    }
    _write_json(state_root / "factory-last-run.json", summary)
    return summary


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    state_root = root / "state"
    try:
        with FactoryLock(state_root / "factory.lock"):
            summary = run_once(root)
    except RuntimeError as exc:
        if str(exc) == "factory already running":
            return
        raise
    except Exception as exc:
        _write_json(
            state_root / "factory-last-error.json",
            {"state": "UNHANDLED_ERROR", "time_unix": time.time(), "type": type(exc).__name__, "message": str(exc)[:4000]},
        )
        raise

    _write_json(state_root / "factory-heartbeat.json", {"time_unix": time.time(), "state": summary["state"]})


if __name__ == "__main__":
    main()
