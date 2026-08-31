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

def connect_mcp_server(server_url: str) -> str:
    """Connects a new Model Context Protocol (MCP) server by URL and saves it."""
    from core.config_manager import add_mcp_server
    ok, msg = add_mcp_server(server_url)
    return msg

def disconnect_mcp_server(server_url_or_index: str) -> str:
    """Disconnects and removes an MCP server from active configuration."""
    from core.config_manager import remove_mcp_server
    ok, msg = remove_mcp_server(server_url_or_index)
    return msg

def call_mcp_tool_direct(tool_name: str, json_args_str: str = "{}") -> str:
    """Directly tests and executes an MCP tool with a raw JSON argument string."""
    try:
        args = json.loads(json_args_str) if json_args_str.strip() else {}
        return execute_mcp_tool(tool_name, args)
    except Exception as e:
        return f"Invalid JSON arguments: {e}"
