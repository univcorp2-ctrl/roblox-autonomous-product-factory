from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
LATEST_PROTOCOL = "2026-07-28"
LEGACY_PROTOCOL = "2025-11-25"


class McpError(RuntimeError):
    pass


class StudioMcpClient:
    def __init__(self, launcher: Path | None = None):
        local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
        self.launcher = launcher or (local / "Roblox" / "mcp.bat")
        self.proc: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._next_id = 1
        self._modern = False

    def start(self) -> None:
        if os.name != "nt":
            raise McpError("Roblox Studio MCP local runner currently requires Windows")
        if not self.launcher.exists():
            raise McpError(f"Studio MCP launcher missing: {self.launcher}. Log in to Studio and enable 'Studio as MCP server'.")
        self.proc = subprocess.Popen(
            ["cmd.exe", "/c", str(self.launcher)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        threading.Thread(target=self._reader, daemon=True).start()
        try:
            self._discover_modern()
            self._modern = True
        except Exception:
            self._legacy_initialize()
            self._modern = False

    def _reader(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "id" in message:
                self._responses.put(message)

    def _write(self, message: dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise McpError("MCP client is not started")
        self.proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()

    def _request_raw(self, method: str, params: dict[str, Any], timeout: float = 12) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        deferred: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            try:
                response = self._responses.get(timeout=min(0.5, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if response.get("id") == request_id:
                for item in deferred:
                    self._responses.put(item)
                if "error" in response:
                    raise McpError(f"MCP {method} error: {response['error']}")
                return response.get("result", {})
            deferred.append(response)
        for item in deferred:
            self._responses.put(item)
        raise McpError(f"MCP request timed out: {method}")

    @staticmethod
    def _modern_meta() -> dict[str, Any]:
        return {
            "io.modelcontextprotocol/protocolVersion": LATEST_PROTOCOL,
            "io.modelcontextprotocol/clientInfo": {"name": "roblox-autonomous-product-factory", "version": "0.1.0"},
            "io.modelcontextprotocol/clientCapabilities": {},
        }

    def _discover_modern(self) -> None:
        result = self._request_raw("server/discover", {"_meta": self._modern_meta()}, timeout=5)
        versions = result.get("supportedVersions", [])
        if not versions:
            raise McpError("modern discovery returned no supported versions")

    def _legacy_initialize(self) -> None:
        result = self._request_raw(
            "initialize",
            {
                "protocolVersion": LEGACY_PROTOCOL,
                "capabilities": {},
                "clientInfo": {"name": "roblox-autonomous-product-factory", "version": "0.1.0"},
            },
            timeout=8,
        )
        if not result:
            raise McpError("legacy initialize failed")
        self._write({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 20) -> dict[str, Any]:
        payload = dict(params or {})
        if self._modern:
            payload.setdefault("_meta", self._modern_meta())
        return self._request_raw(method, payload, timeout=timeout)

    def list_tools(self) -> list[dict[str, Any]]:
        result = self.request("tools/list", {})
        return list(result.get("tools", []))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments}, timeout=60)

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
