import json
import os
import sys
import subprocess
import threading
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

class StdioMCPServer:
    """Manages a stdio-based subprocess MCP Server (JSON-RPC over stdin/stdout)."""
    
    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._req_id = 0

    def _get_process(self) -> subprocess.Popen:
        if self.process is None or self.process.poll() is not None:
            cmd = [self.command] + self.args
            full_env = os.environ.copy()
            full_env.update(self.env)
            full_env["MCP_MODE"] = "stdio"
            full_env["LOG_LEVEL"] = "error"
            full_env["DISABLE_CONSOLE_OUTPUT"] = "true"

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=full_env
            )
            # Send MCP initialization handshake
            self._send_raw({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "WednesdayAI", "version": "1.0"}
                }
            })
            # Read init response
            self.process.stdout.readline()
            # Send initialized notification
            self._send_raw({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self.process

    def _send_raw(self, payload: Dict[str, Any]):
        if self.process and self.process.stdin:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()

    def call_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            proc = self._get_process()
            self._req_id += 1
            req_id = self._req_id
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params
            }
            self._send_raw(payload)
            line = proc.stdout.readline()
            if not line:
                return {"error": {"message": "Empty response from stdio MCP server."}}
            try:
                return json.loads(line)
            except Exception as e:
                return {"error": {"message": f"Invalid JSON response: {e}"}}

    def list_tools(self) -> List[Dict[str, Any]]:
        res = self.call_method("tools/list", {})
        return res.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        res = self.call_method("tools/call", {"name": tool_name, "arguments": arguments})
        if "error" in res:
            return f"MCP Error: {res['error'].get('message', res['error'])}"
        content = res.get("result", {}).get("content", [])
        if isinstance(content, list):
            texts = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
            if texts:
                return "\n".join(texts)
        return json.dumps(res.get("result", {}), default=str)


class MCPClient:
    """
    Unified Model Context Protocol (MCP) Client.
    Discovers tools from HTTP / SSE endpoints and stdio subprocess servers (like n8n-mcp),
    formatting them for Gemini and Groq function calling.
    """

    def __init__(self):
        self.http_servers: List[str] = self._load_server_endpoints()
        self.stdio_servers: Dict[str, StdioMCPServer] = {}
        self.cached_tools: Dict[str, Dict[str, Any]] = {}
        self._init_global_stdio_servers()

    def _load_server_endpoints(self) -> List[str]:
        endpoints = []
        raw = getattr(config, "MCP_SERVERS", "")
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    endpoints.extend(parsed)
                elif isinstance(parsed, dict):
                    endpoints.extend(parsed.values())
            except Exception:
                for item in raw.split(","):
                    if item.strip():
                        endpoints.append(item.strip())
        return endpoints

    def _init_global_stdio_servers(self):
        """Loads stdio MCP servers configured in ~/.gemini/config/mcp_config.json or n8n-mcp."""
        # 1. Look for n8n-mcp default globally installed
        npm_n8n_path = Path(os.environ.get("USERPROFILE", "")) / r"AppData\Roaming\npm\node_modules\n8n-mcp\dist\mcp\index.js"
        if npm_n8n_path.exists():
            self.stdio_servers["n8n-mcp"] = StdioMCPServer(
                name="n8n-mcp",
                command="node",
                args=[str(npm_n8n_path)],
                env={
                    "N8N_API_URL": getattr(config, "N8N_BASE_URL", "http://localhost:5678"),
                    "N8N_BASE_URL": getattr(config, "N8N_BASE_URL", "http://localhost:5678"),
                    "N8N_API_KEY": getattr(config, "N8N_API_KEY", "")
                }
            )

        # 2. Check global mcp_config.json
        cfg_file = Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "config" / "mcp_config.json"
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    for s_name, s_conf in cfg.get("mcpServers", {}).items():
                        cmd = s_conf.get("command")
                        args = s_conf.get("args", [])
                        env = s_conf.get("env", {})
                        if cmd and s_name not in self.stdio_servers:
                            self.stdio_servers[s_name] = StdioMCPServer(s_name, cmd, args, env)
            except Exception:
                pass

    def refresh_tools(self) -> Dict[str, Dict[str, Any]]:
        """Queries all HTTP and stdio MCP servers using JSON-RPC 'tools/list'."""
        all_tools = {}

        # 1. HTTP / SSE servers
        for server_url in self.http_servers:
            try:
                payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
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
                                "type": "http",
                                "server_url": server_url,
                                "schema": t
                            }
            except Exception:
                pass

        # 2. Stdio subprocess servers
        for s_name, server in self.stdio_servers.items():
            try:
                tools = server.list_tools()
                for t in tools:
                    t_name = t.get("name")
                    if t_name:
                        all_tools[t_name] = {
                            "type": "stdio",
                            "server_name": s_name,
                            "server_instance": server,
                            "schema": t
                        }
            except Exception:
                pass

        self.cached_tools = all_tools
        return self.cached_tools

    def get_tool_definitions_for_groq(self) -> List[Dict[str, Any]]:
        """Converts discovered MCP tools into Groq / OpenAI tool definition format."""
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
        """Calls a tool on its respective MCP server (stdio or HTTP)."""
        clean_name = tool_name.removeprefix("mcp_")
        if clean_name not in self.cached_tools:
            self.refresh_tools()

        info = self.cached_tools.get(clean_name)
        if not info:
            return f"MCP Tool '{clean_name}' not found on any active MCP server."

        # Stdio tool execution
        if info.get("type") == "stdio":
            server: StdioMCPServer = info["server_instance"]
            return server.call_tool(clean_name, arguments)

        # HTTP tool execution
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
                content = data.get("result", {}).get("content", [])
                if isinstance(content, list):
                    texts = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
                    if texts:
                        return "\n".join(texts)
                return json.dumps(data.get("result", {}), default=str)
            return f"MCP Server returned HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Failed to execute MCP tool '{clean_name}': {e}"

# Global singleton
mcp_client = MCPClient()
