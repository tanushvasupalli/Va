import io
import json
import requests
from typing import Optional, Dict, Any, Tuple
import config

def _get_pc_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-PC-SECRET": getattr(config, "PC_AGENT_KEY", "wednesday_pc_secret")
    }

def _pc_base_url() -> str:
    return getattr(config, "PC_AGENT_URL", "http://localhost:8085").rstrip("/")

def check_pc_status() -> str:
    """Checks if the remote PC companion agent is online and responsive."""
    url = f"{_pc_base_url()}/status"
    try:
        res = requests.get(url, headers=_get_pc_headers(), timeout=5)
        if res.status_code == 200:
            data = res.json()
            return f"PC Online ({data.get('hostname', 'Windows PC')}) | CPU: {data.get('cpu_percent')}% | RAM: {data.get('ram_used_gb')}GB / {data.get('ram_total_gb')}GB"
        return f"PC returned HTTP {res.status_code}"
    except Exception as e:
        return f"PC unreachable at {_pc_base_url()}: {e}"

def read_remote_pc_file(file_path: str) -> str:
    """Reads text content of a file located on the remote Windows PC."""
    url = f"{_pc_base_url()}/files/read"
    try:
        res = requests.get(url, params={"path": file_path}, headers=_get_pc_headers(), timeout=10)
        if res.status_code == 200:
            data = res.json()
            return f"File content of '{file_path}':\n{data.get('content', '')}"
        return f"Error reading PC file: {res.json().get('error', res.text)}"
    except Exception as e:
        return f"Failed to connect to PC agent: {e}"

def list_remote_pc_directory(folder_path: str = "Desktop") -> str:
    """Lists files and folders in a directory on the remote Windows PC."""
    url = f"{_pc_base_url()}/files/list"
    try:
        res = requests.get(url, params={"path": folder_path}, headers=_get_pc_headers(), timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get("items", [])
            if not items:
                return f"Directory '{folder_path}' on PC is empty."
            lines = [f"Contents of '{data.get('resolved_path', folder_path)}' on PC:"]
            for item in items[:40]:
                tag = "[DIR]" if item.get("is_dir") else f"[{item.get('size_str', 'File')}]"
                lines.append(f"  {tag} {item.get('name')}")
            return "\n".join(lines)
        return f"Error listing PC directory: {res.json().get('error', res.text)}"
    except Exception as e:
        return f"Failed to connect to PC agent: {e}"

def search_remote_pc_files(query: str, search_in: str = "Desktop") -> str:
    """Searches for files matching a pattern on the remote Windows PC."""
    url = f"{_pc_base_url()}/files/search"
    try:
        res = requests.get(url, params={"query": query, "path": search_in}, headers=_get_pc_headers(), timeout=15)
        if res.status_code == 200:
            data = res.json()
            matches = data.get("matches", [])
            if not matches:
                return f"No files matching '{query}' found in '{search_in}' on your PC."
            lines = [f"Found {len(matches)} matching files on PC:"]
            for m in matches[:25]:
                lines.append(f"• {m.get('name')} ({m.get('path')}) [{m.get('size_str', '')}]")
            return "\n".join(lines)
        return f"Error searching PC files: {res.json().get('error', res.text)}"
    except Exception as e:
        return f"Failed to connect to PC agent: {e}"

def write_remote_pc_file(file_path: str, content: str) -> str:
    """Writes text content to a file on the remote Windows PC."""
    url = f"{_pc_base_url()}/files/write"
    try:
        payload = {"path": file_path, "content": content}
        res = requests.post(url, json=payload, headers=_get_pc_headers(), timeout=10)
        if res.status_code == 200:
            return f"Successfully saved file to PC at '{file_path}'."
        return f"Error saving PC file: {res.json().get('error', res.text)}"
    except Exception as e:
        return f"Failed to connect to PC agent: {e}"

def download_pc_file_bytes(file_path: str) -> Tuple[Optional[bytes], str]:
    """Downloads raw file bytes from the remote PC (for sending over Telegram)."""
    url = f"{_pc_base_url()}/files/download"
    try:
        res = requests.get(url, params={"path": file_path}, headers=_get_pc_headers(), timeout=20)
        if res.status_code == 200:
            filename = res.headers.get("X-Filename", file_path.split("/")[-1].split("\\")[-1])
            return res.content, filename
        return None, f"Error: {res.text}"
    except Exception as e:
        return None, f"Connection failed: {e}"

def control_remote_pc_power(action: str = "status") -> str:
    """Controls power/state of the remote PC (sleep, lock, hibernate, restart, shutdown, cancel)."""
    url = f"{_pc_base_url()}/power"
    try:
        res = requests.post(url, json={"action": action}, headers=_get_pc_headers(), timeout=10)
        if res.status_code == 200:
            return res.json().get("message", f"Command '{action}' executed on PC.")
        return f"Error controlling PC power: {res.text}"
    except Exception as e:
        return f"Failed to reach PC agent: {e}"

def exec_remote_pc_command(command: str) -> str:
    """Executes a PowerShell / CMD command on the remote PC."""
    url = f"{_pc_base_url()}/exec"
    try:
        res = requests.post(url, json={"command": command}, headers=_get_pc_headers(), timeout=25)
        if res.status_code == 200:
            data = res.json()
            out = data.get("output", "").strip()
            err = data.get("error", "").strip()
            res_str = out if out else (f"Error: {err}" if err else "Command executed successfully (no output).")
            return f"PC Command Output:\n{res_str}"
        return f"PC Command failed (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"Failed to execute command on PC: {e}"
