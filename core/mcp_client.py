import json
import os
import requests
from typing import List, Dict, Any, Optional
import config

class MCPClient:
    """
    Lightweight Model Context Protocol (MCP) Client.
    Discovers tools from configured MCP servers (HTTP / SSE / JSON-RPC)
    and formats them for Gemini and Groq function calling.
    """

    def __init__(self):
        self.servers: List[str] = self._load_server_endpoints()
        self.cached_tools: Dict[str, Dict[str, Any]] = {}

    def _load_server_endpoints(self) -> List[str]:
        endpoints = []
        raw = getattr(config, "MCP_SERVERS", "")
        if raw:
            try:
                # Check if JSON array
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    endpoints.extend(parsed)
                elif isinstance(parsed, dict):
                    endpoints.extend(parsed.values())
            except Exception:
                # Comma-separated list
                for item in raw.split(","):
                    if item.strip():
                        endpoints.append(item.strip())
        return endpoints

    def add_server(self, server_url: str):
        """Adds an MCP server endpoint at runtime."""
        if server_url and server_url not in self.servers:
            self.servers.append(server_url)

    def refresh_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Queries all configured MCP servers using the JSON-RPC 'tools/list' standard.
        """
        all_tools = {}
        for server_url in self.servers:
            try:
                # Standard MCP JSON-RPC call for tools/list
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }
                # Handle SSE or standard POST endpoint
                target = server_url
                if target.endswith("/sse"):
                    target = target.replace("/sse", "/message")
                elif not target.endswith("/tools/list") and not target.endswith("/jsonrpc"):
                    target = target.rstrip("/") + "/jsonrpc"

                res = requests.post(target, json=payload, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    tools = data.get("result", {}).get("tools", [])
                    for t in tools:
                        tool_name = t.get("name")
                        if tool_name:
                            all_tools[tool_name] = {
                                "server_url": server_url,
                                "schema": t
                            }
            except Exception as e:
                # Silent notice to avoid blocking if an external server is down
                pass

        self.cached_tools = all_tools
        return self.cached_tools

    def get_tool_definitions_for_groq(self) -> List[Dict[str, Any]]:
        """
        Converts discovered MCP tools into Groq / OpenAI tool definition format.
        """
        definitions = []
        for name, info in self.cached_tools.items():
            schema = info.get("schema", {})
            definitions.append({
                "type": "function",
                "function": {
                    "name": f"mcp_{name}",
                    "description": schema.get("description", f"MCP Tool: {name}"),
                    "parameters": schema.get("inputSchema", {
                        "type": "object",
                        "properties": {}
                    })
                }
            })
        return definitions

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Calls a tool on its respective MCP server using JSON-RPC 'tools/call'.
        """
        clean_name = tool_name.removeprefix("mcp_")
        if clean_name not in self.cached_tools:
            # Try refreshing in case it was recently loaded
            self.refresh_tools()

        info = self.cached_tools.get(clean_name)
        if not info:
            return f"MCP Tool '{clean_name}' not found on any active MCP server."

        server_url = info["server_url"]
        target = server_url
        if target.endswith("/sse"):
            target = target.replace("/sse", "/message")
        elif not target.endswith("/jsonrpc"):
            target = target.rstrip("/") + "/jsonrpc"

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": clean_name,
                "arguments": arguments
            }
        }

        try:
            res = requests.post(target, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                result = data.get("result", {})
                content = result.get("content", [])
                if isinstance(content, list):
                    texts = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
                    if texts:
                        return "\n".join(texts)
                return json.dumps(result, default=str)
            return f"MCP Server returned HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Failed to execute MCP tool '{clean_name}': {e}"

# Global singleton
mcp_client = MCPClient()
