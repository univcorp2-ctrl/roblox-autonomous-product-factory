from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


BASE = "https://apis.roblox.com"


class OpenCloudError(RuntimeError):
    pass


@dataclass(frozen=True)
class LuauTaskRef:
    session_id: str
    task_id: str


class OpenCloudClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("api key required")
        self._api_key = api_key

    def _request(self, method: str, path: str, *, body: bytes | None = None, content_type: str | None = None) -> tuple[int, bytes]:
        headers = {"x-api-key": self._api_key, "User-Agent": "RobloxAutonomousProductFactory/0.1"}
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise OpenCloudError(f"Roblox Open Cloud HTTP {exc.code}: {detail}") from exc

    def publish_place(self, universe_id: str, place_id: str, artifact: Path, version_type: str) -> str:
        if version_type not in {"Saved", "Published"}:
            raise ValueError("version_type must be Saved or Published")
        query = urllib.parse.urlencode({"versionType": version_type})
        path = f"/universes/v1/{universe_id}/places/{place_id}/versions?{query}"
        _, body = self._request("POST", path, body=artifact.read_bytes(), content_type="application/octet-stream")
        text = body.decode("utf-8", errors="replace").strip().strip('"')
        if not text:
            raise OpenCloudError("publish response did not include a version")
        return text

    def create_luau_task(self, universe_id: str, place_id: str, version_id: str, script: str) -> LuauTaskRef:
        path = f"/cloud/v2/universes/{universe_id}/places/{place_id}/versions/{version_id}/luau-execution-session-tasks"
        payload = json.dumps({"script": script}).encode("utf-8")
        _, body = self._request("POST", path, body=payload, content_type="application/json")
        data = json.loads(body)
        resource_path = str(data.get("path", ""))
        match = re.search(r"luau-execution-sessions/([^/]+)/tasks/([^/]+)", resource_path)
        if not match:
            raise OpenCloudError(f"unrecognized Luau task path: {resource_path[:500]}")
        return LuauTaskRef(match.group(1), match.group(2))

    def get_luau_task(self, universe_id: str, place_id: str, version_id: str, ref: LuauTaskRef) -> dict:
        path = (
            f"/cloud/v2/universes/{universe_id}/places/{place_id}/versions/{version_id}"
            f"/luau-execution-sessions/{ref.session_id}/tasks/{ref.task_id}"
        )
        _, body = self._request("GET", path)
        return json.loads(body)

    def get_luau_logs(self, universe_id: str, place_id: str, version_id: str, ref: LuauTaskRef) -> dict:
        path = (
            f"/cloud/v2/universes/{universe_id}/places/{place_id}/versions/{version_id}"
            f"/luau-execution-sessions/{ref.session_id}/tasks/{ref.task_id}/logs"
        )
        _, body = self._request("GET", path)
        return json.loads(body)

    def wait_luau_task(self, universe_id: str, place_id: str, version_id: str, ref: LuauTaskRef) -> tuple[dict, dict]:
        # Bounded polling: three checks, at least eight seconds apart. A slow task
        # is quarantined rather than causing an unbounded automation loop.
        last: dict = {}
        for _ in range(3):
            time.sleep(10)
            last = self.get_luau_task(universe_id, place_id, version_id, ref)
            state = str(last.get("state", "")).upper()
            if any(token in state for token in ("COMPLETED", "SUCCEEDED", "SUCCESS", "FAILED", "ERROR", "CANCEL")):
                logs = self.get_luau_logs(universe_id, place_id, version_id, ref)
                return last, logs
        raise OpenCloudError(f"Luau task did not reach terminal state in bounded polling: {last.get('state')}")
