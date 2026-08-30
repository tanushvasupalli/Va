import json
from typing import Dict, Any, Optional
from core.mcp_client import mcp_client

def list_connected_mcp_tools() -> str:
    """Returns a list of all currently discovered tools from MCP servers."""
    tools = mcp_client.refresh_tools()
    if not tools:
        return "No external MCP servers are currently connected. Configure MCP_SERVERS in .env to connect MCP tools."
    
    lines = ["Discovered MCP Tools:"]
    for name, data in tools.items():
        desc = data.get("schema", {}).get("description", "No description")
        server = data.get("server_url", "unknown")
        lines.append(f"• {name} (from {server}): {desc}")
    return "\n".join(lines)

def execute_mcp_tool(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """Executes a discovered MCP tool with given arguments."""
    args = arguments or {}
    return mcp_client.call_tool(tool_name, args)
