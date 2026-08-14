from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .config import load_product
from .gitops import sync_repo
from .models import GateResult, ReleaseResult
from .opencloud import OpenCloudClient, OpenCloudError
from .process import CommandFailed, run
from .studio_gate import run_studio_gate


def _state_path(state_root: Path, name: str) -> Path:
    state_root.mkdir(parents=True, exist_ok=True)
    return state_root / f"{name}.json"


def _save(result: ReleaseResult, state_root: Path) -> None:
    payload = asdict(result)
    if result.artifact_path is not None:
        payload["artifact_path"] = str(result.artifact_path)
    _state_path(state_root, result.product).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run_product(manifest: Path, work_root: Path, state_root: Path) -> ReleaseResult:
    product = load_product(manifest)
    repo = work_root / product.name
    gates: list[GateResult] = []

    try:
        sync_repo(product.repo_url, product.branch, repo)
        gates.append(GateResult("git_sync", True, "repository synchronized"))
        for command in product.build_commands:
            run(command, repo)
        artifact = repo / product.artifact
        if not artifact.exists() or artifact.stat().st_size < 1000:
            raise CommandFailed(f"artifact missing or too small: {artifact}")
        gates.append(GateResult("build", True, "build commands passed", {"artifact_bytes": artifact.stat().st_size}))
    except (CommandFailed, OSError) as exc:
        result = ReleaseResult(product.name, "QUARANTINED_BUILD", tuple(gates + [GateResult("build", False, str(exc))]))
        _save(result, state_root)
        return result

    if product.require_studio_mcp:
        studio = run_studio_gate()
        gates.append(studio)
        if not studio.passed:
            result = ReleaseResult(product.name, "READY_WAITING_STUDIO_MCP", tuple(gates), artifact)
            _save(result, state_root)
            return result

    api_key = os.environ.get("ROBLOX_OPEN_CLOUD_API_KEY", "")
    test_universe = os.environ.get("ROBLOX_TEST_UNIVERSE_ID", "")
    test_place = os.environ.get("ROBLOX_TEST_PLACE_ID", "")
    if not (api_key and test_universe and test_place and product.opencloud_smoke_script):
        result = ReleaseResult(product.name, "READY_WAITING_OPEN_CLOUD_CREDENTIALS", tuple(gates), artifact)
        _save(result, state_root)
        return result

    client = OpenCloudClient(api_key)
    try:
        saved_version = client.publish_place(test_universe, test_place, artifact, "Saved")
        gates.append(GateResult("opencloud_saved", True, "uploaded to isolated test place as Saved", {"version": saved_version}))
        smoke_script = (repo / product.opencloud_smoke_script).read_text(encoding="utf-8")
        ref = client.create_luau_task(test_universe, test_place, saved_version, smoke_script)
        task, logs = client.wait_luau_task(test_universe, test_place, saved_version, ref)
        state_text = str(task.get("state", "")).upper()
        passed = any(token in state_text for token in ("COMPLETED", "SUCCEEDED", "SUCCESS")) and not any(token in state_text for token in ("FAILED", "ERROR"))
        gates.append(GateResult("opencloud_luau", passed, f"headless test state: {state_text}", {"logs": logs}))
        if not passed:
            result = ReleaseResult(product.name, "QUARANTINED_HEADLESS_TEST", tuple(gates), artifact)
            _save(result, state_root)
            return result
    except (OpenCloudError, OSError, ValueError) as exc:
        result = ReleaseResult(product.name, "QUARANTINED_OPEN_CLOUD", tuple(gates + [GateResult("opencloud", False, str(exc))]), artifact)
        _save(result, state_root)
        return result

    if os.environ.get("AUTO_PUBLISH", "0") != "1":
        result = ReleaseResult(product.name, "RELEASE_CANDIDATE", tuple(gates), artifact)
        _save(result, state_root)
        return result

    prod_universe = os.environ.get("ROBLOX_PRODUCTION_UNIVERSE_ID", "")
    prod_place = os.environ.get("ROBLOX_PRODUCTION_PLACE_ID", "")
    if not (prod_universe and prod_place):
        result = ReleaseResult(product.name, "READY_WAITING_PRODUCTION_IDS", tuple(gates), artifact)
        _save(result, state_root)
        return result

    try:
        published = client.publish_place(prod_universe, prod_place, artifact, "Published")
        gates.append(GateResult("publish", True, "published after all configured gates passed", {"version": published}))
        result = ReleaseResult(product.name, "PUBLISHED", tuple(gates), artifact, published)
    except OpenCloudError as exc:
        result = ReleaseResult(product.name, "QUARANTINED_PUBLISH", tuple(gates + [GateResult("publish", False, str(exc))]), artifact)
    _save(result, state_root)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", default="products")
    parser.add_argument("--work-root", default=os.environ.get("FACTORY_WORK_ROOT", "work/repos"))
    parser.add_argument("--state-root", default=os.environ.get("FACTORY_STATE_ROOT", "state"))
    args = parser.parse_args()
    product_dir = Path(args.products)
    results = [run_product(path, Path(args.work_root), Path(args.state_root)) for path in sorted(product_dir.glob("*.toml"))]
    print(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
