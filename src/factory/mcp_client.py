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
PROTOCOL_VERSION = "2025-11-25"


class McpError(RuntimeError):
    pass


class StudioMcpClient:
    def __init__(self, launcher: Path | None = None):
        local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
        self.launcher = launcher or (local / "Roblox" / "mcp.bat")
        self.proc: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._next_id = 1
        self.protocol_version = PROTOCOL_VERSION

    def start(self) -> None:
        if os.name != "nt":
            raise McpError("Roblox Studio MCP local runner currently requires Windows")
        if not self.launcher.exists():
            raise McpError(f"Studio MCP launcher missing: {self.launcher}. Log in to Studio and enable 'Studio as MCP server'.")

        self.proc = subprocess.Popen(
            ["cmd.exe", "/c", str(self.launcher), "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        threading.Thread(target=self._reader, daemon=True).start()

        result = self._request_raw(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "roblox-autonomous-product-factory", "version": "0.1.0"},
            },
            timeout=8,
        )
        negotiated = result.get("protocolVersion")
        if isinstance(negotiated, str) and negotiated:
            self.protocol_version = negotiated
        if not result.get("serverInfo"):
            raise McpError("Studio MCP initialize response missing serverInfo")
        self._write({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

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
        if not self.proc or not self.proc.stdin or self.proc.poll() is not None:
            raise McpError("MCP process is not running")
        try:
            self.proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
            self.proc.stdin.flush()
        except OSError as exc:
            raise McpError(f"failed writing to Studio MCP process: {exc}") from exc

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
                if self.proc and self.proc.poll() is not None:
                    raise McpError(f"Studio MCP exited while waiting for {method}")
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

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 20) -> dict[str, Any]:
        return self._request_raw(method, dict(params or {}), timeout=timeout)

    def list_tools(self, attempts: int = 3) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                result = self.request("tools/list", {}, timeout=12)
                tools = list(result.get("tools", []))
                if tools:
                    return tools
            except McpError as exc:
                last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2)
        if last_error:
            raise McpError(f"Studio MCP tools were not ready: {last_error}")
        raise McpError("Studio MCP returned no tools")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments}, timeout=60)

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
