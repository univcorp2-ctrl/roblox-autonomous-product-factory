from __future__ import annotations

from .mcp_client import McpError, StudioMcpClient
from .models import GateResult


REQUIRED = {
    "get_studio_state",
    "search_game_tree",
    "execute_luau",
    "start_stop_play",
    "get_console_output",
    "screen_capture",
}


def _arguments_for_execute(tool: dict, code: str) -> dict:
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    args = {}
    for key in ("code", "script", "source"):
        if key in properties:
            args[key] = code
            break
    if not args:
        args["code"] = code
    for key in ("datamodel_type", "dataModelType", "datamodelType"):
        if key in properties:
            args[key] = "Edit"
            break
    return args


def run_studio_gate() -> GateResult:
    client = StudioMcpClient()
    try:
        client.start()
        tools = client.list_tools()
        by_name = {tool.get("name"): tool for tool in tools}
        missing = sorted(REQUIRED - set(by_name))
        if missing:
            return GateResult("studio_mcp", False, f"required tools missing: {missing}", {"available": sorted(by_name)})
        state = client.call_tool("get_studio_state", {})
        execute = client.call_tool(
            "execute_luau",
            _arguments_for_execute(
                by_name["execute_luau"],
                "return {placeId = game.PlaceId, gameName = game.Name, hasWorkspace = workspace ~= nil}",
            ),
        )
        return GateResult("studio_mcp", True, "Studio MCP connected and Edit DataModel smoke passed", {"state": state, "execute": execute})
    except McpError as exc:
        return GateResult("studio_mcp", False, str(exc), {})
    finally:
        client.close()
