import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import config

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

SENSITIVE_KEYS = {
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "SUPABASE_KEY",
    "SUPABASE_DATABASE_URL",
    "TELEGRAM_BOT_TOKEN",
    "N8N_API_KEY",
    "PC_AGENT_KEY"
}

def mask_value(key: str, value: str) -> str:
    """Masks sensitive secret keys for safe display in Telegram/UI."""
    if not value or value.strip() == "":
        return "(Not Configured)"
    if key.upper() in SENSITIVE_KEYS:
        val_str = str(value).strip()
        if len(val_str) <= 8:
            return "********"
        return f"{val_str[:4]}...{val_str[-4:]}"
    return str(value)

def read_raw_env() -> Dict[str, str]:
    """Reads all key-value pairs from .env directly."""
    data = {}
    if not ENV_PATH.exists():
        return data
    try:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                data[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[ConfigManager] Error reading .env: {e}")
    return data

def get_all_configs(mask_secrets: bool = True) -> Dict[str, str]:
    """Returns all current configurations with optional secret masking."""
    raw = read_raw_env()
    
    # Also grab in-memory settings from config.py
    keys = [
        "GROQ_API_KEY", "GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_ID", "GEMINI_MODEL",
        "GROQ_MODEL", "TTS_VOICE", "MUTE_AGENT_VOICE", "PLAY_CHIMES",
        "PC_AGENT_URL", "PC_AGENT_KEY", "LOCAL_SUBNET", "PC_MAC_ADDRESS",
        "N8N_BASE_URL", "N8N_WEBHOOK_URL", "N8N_API_KEY", "MCP_SERVERS"
    ]
    
    result = {}
    for k in keys:
        val = raw.get(k)
        if val is None:
            val = getattr(config, k, "")
        val_str = str(val) if val is not None else ""
        result[k] = mask_value(k, val_str) if mask_secrets else val_str
        
    return result

def get_config_value(key: str, mask_secrets: bool = False) -> str:
    """Gets value for a specific setting key."""
    clean_k = key.strip().upper()
    raw = read_raw_env()
    val = raw.get(clean_k)
    if val is None:
        val = getattr(config, clean_k, "")
    val_str = str(val) if val is not None else ""
    return mask_value(clean_k, val_str) if mask_secrets else val_str

def set_config_value(key: str, value: str) -> Tuple[bool, str]:
    """
    Updates or inserts KEY=VALUE in .env, updates os.environ,
    and hot-updates in-memory config module attributes.
    """
    clean_k = key.strip().upper()
    clean_v = str(value).strip()
    
    if not clean_k:
        return False, "Configuration key cannot be empty."

    try:
        # 1. Read existing .env lines or create new
        if ENV_PATH.exists():
            lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        else:
            lines = []

        found = False
        new_lines = []
        pattern = re.compile(rf"^\s*{re.escape(clean_k)}\s*=")

        for line in lines:
            if pattern.match(line):
                new_lines.append(f"{clean_k}={clean_v}")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"{clean_k}={clean_v}")

        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        # 2. Update os.environ
        os.environ[clean_k] = clean_v

        # 3. Hot-update config module
        if hasattr(config, clean_k):
            orig = getattr(config, clean_k)
            if isinstance(orig, bool):
                setattr(config, clean_k, clean_v.lower() in ("true", "1", "yes"))
            elif isinstance(orig, int):
                try:
                    setattr(config, clean_k, int(clean_v))
                except ValueError:
                    setattr(config, clean_k, clean_v)
            else:
                setattr(config, clean_k, clean_v)
        else:
            setattr(config, clean_k, clean_v)

        # 4. Handle specific component dynamic updates
        if clean_k == "TTS_VOICE":
            from core.speaker import speaker
            speaker.default_voice = clean_v
        elif clean_k == "MUTE_AGENT_VOICE":
            from core.speaker import speaker
            speaker.set_muted(clean_v.lower() in ("true", "1", "yes"))
        elif clean_k in ("GROQ_MODEL", "GEMINI_MODEL"):
            from core.brain import brain
            brain.set_model(clean_v)
        elif clean_k in ("GROQ_API_KEY", "GEMINI_API_KEY"):
            from core.brain import brain
            brain._init_clients()

        masked = mask_value(clean_k, clean_v)
        return True, f"Setting *{clean_k}* successfully updated to `{masked}`."

    except Exception as e:
        return False, f"Failed to update setting {clean_k}: {e}"

def get_mcp_servers() -> List[str]:
    """Returns list of currently configured MCP server endpoints."""
    raw = get_config_value("MCP_SERVERS", mask_secrets=False)
    if not raw:
        return []
    servers = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            servers = [str(x).strip() for x in parsed if str(x).strip()]
        elif isinstance(parsed, dict):
            servers = [str(x).strip() for x in parsed.values() if str(x).strip()]
    except Exception:
        servers = [s.strip() for s in raw.split(",") if s.strip()]
    return servers

def add_mcp_server(server_url: str) -> Tuple[bool, str]:
    """
    Connects a new MCP server, verifies tool discovery, and persists to .env.
    """
    url = server_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return False, f"Invalid MCP server URL: `{url}`. Must start with http:// or https://"

    current = get_mcp_servers()
    if url in current:
        return True, f"MCP server `{url}` is already registered."

    current.append(url)
    csv_str = ",".join(current)
    ok, msg = set_config_value("MCP_SERVERS", csv_str)
    if not ok:
        return False, msg

    # Refresh in-memory MCP client
    from core.mcp_client import mcp_client
    mcp_client.servers = current
    tools = mcp_client.refresh_tools()
    
    found_count = len([t for t, data in tools.items() if data.get("server_url") == url])
    return True, f"✅ MCP Server `{url}` connected successfully! Discovered {found_count} new tools."

def remove_mcp_server(server_url_or_index: str) -> Tuple[bool, str]:
    """
    Disconnects and removes an MCP server from configuration.
    """
    target = server_url_or_index.strip()
    current = get_mcp_servers()
    
    if not current:
        return False, "No MCP servers are currently configured."

    matched = None
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(current):
            matched = current[idx]
    else:
        for s in current:
            if target.lower() in s.lower():
                matched = s
                break

    if not matched:
        return False, f"Could not find MCP server matching `{target}`."

    current.remove(matched)
    csv_str = ",".join(current)
    ok, msg = set_config_value("MCP_SERVERS", csv_str)
    if not ok:
        return False, msg

    # Refresh in-memory MCP client
    from core.mcp_client import mcp_client
    mcp_client.servers = current
    mcp_client.refresh_tools()
    return True, f"🗑 MCP Server `{matched}` removed and disconnected."
