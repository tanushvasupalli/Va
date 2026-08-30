import os
import sys
import time
import socket
import fnmatch
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import psutil

import config

app = FastAPI(title="Wednesday PC Companion Agent", version="1.0.0")

PC_SECRET = getattr(config, "PC_AGENT_KEY", "wednesday_pc_secret")
USER_HOME = Path.home()

def verify_secret(x_pc_secret: Optional[str] = Header(None)):
    if not PC_SECRET or PC_SECRET == "wednesday_pc_secret":
        # Allow default for initial ease of use
        return
    if x_pc_secret != PC_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid X-PC-SECRET")

def resolve_pc_path(path_str: str) -> Path:
    """Resolves Windows path aliases (Desktop, Documents, Downloads) or absolute paths."""
    clean = path_str.strip().strip('"').strip("'")
    lower = clean.lower()
    
    if lower in ("desktop", "my desktop"):
        return USER_HOME / "Desktop"
    elif lower in ("documents", "my documents", "docs"):
        return USER_HOME / "Documents"
    elif lower in ("downloads", "my downloads"):
        return USER_HOME / "Downloads"
    elif lower in ("pictures", "photos"):
        return USER_HOME / "Pictures"
    elif lower in ("music",):
        return USER_HOME / "Music"
    elif lower in ("videos",):
        return USER_HOME / "Videos"
    elif lower in ("home", "user", "~"):
        return USER_HOME
    
    p = Path(clean)
    if not p.is_absolute():
        p = USER_HOME / clean
    return p.resolve()

def format_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{round(bytes_size / 1024, 1)} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{round(bytes_size / (1024 * 1024), 1)} MB"
    return f"{round(bytes_size / (1024 * 1024 * 1024), 2)} GB"

@app.get("/status")
def get_status(x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    mem = psutil.virtual_memory()
    return {
        "status": "online",
        "hostname": socket.gethostname(),
        "platform": sys.platform,
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_percent": mem.percent
    }

@app.get("/files/list")
def list_directory(path: str = Query("Desktop"), x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    target = resolve_pc_path(path)
    if not target.exists():
        return {"error": f"Path '{target}' does not exist on PC.", "items": []}
    if not target.is_dir():
        return {"error": f"Path '{target}' is a file, not a directory.", "items": []}

    items = []
    try:
        for entry in target.iterdir():
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size_bytes": stat.st_size if not entry.is_dir() else 0,
                    "size_str": format_size(stat.st_size) if not entry.is_dir() else "DIR",
                    "path": str(entry)
                })
            except Exception:
                continue
    except Exception as e:
        return {"error": f"Failed to list directory: {e}", "items": []}

    # Sort dirs first, then files alphabetically
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {
        "resolved_path": str(target),
        "count": len(items),
        "items": items
    }

@app.get("/files/read")
def read_file(path: str = Query(...), x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    target = resolve_pc_path(path)
    if not target.exists() or not target.is_file():
        return {"error": f"File '{target}' was not found on PC."}

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(target),
            "filename": target.name,
            "size": len(content),
            "content": content[:20000] # Safe cap
        }
    except Exception as e:
        return {"error": f"Could not read file: {e}"}

@app.get("/files/search")
def search_files(query: str = Query(...), path: str = Query("Desktop"), x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    base = resolve_pc_path(path)
    if not base.exists() or not base.is_dir():
        base = USER_HOME

    pattern = f"*{query.lower().strip()}*"
    matches = []
    try:
        for root, dirs, files in os.walk(base):
            # Limit search depth to avoid infinite scans
            rel = os.path.relpath(root, base)
            if rel.count(os.sep) > 3:
                continue

            for f in files:
                if fnmatch.fnmatch(f.lower(), pattern):
                    full_p = Path(root) / f
                    try:
                        sz = full_p.stat().st_size
                        matches.append({
                            "name": f,
                            "path": str(full_p),
                            "size_bytes": sz,
                            "size_str": format_size(sz)
                        })
                    except Exception:
                        pass
                    if len(matches) >= 50:
                        break
            if len(matches) >= 50:
                break
    except Exception as e:
        return {"error": f"Search error: {e}", "matches": []}

    return {"query": query, "base_path": str(base), "matches": matches}

class WriteFilePayload(BaseModel):
    path: str
    content: str

@app.post("/files/write")
def write_file(payload: WriteFilePayload, x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    target = resolve_pc_path(payload.path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload.content, encoding="utf-8")
        return {"status": "success", "path": str(target), "bytes_written": len(payload.content)}
    except Exception as e:
        return {"error": f"Could not write file: {e}"}

@app.get("/files/download")
def download_file(path: str = Query(...), x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    target = resolve_pc_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(target),
        filename=target.name,
        headers={"X-Filename": target.name}
    )

class PowerPayload(BaseModel):
    action: str = "status"

@app.post("/power")
def control_power(payload: PowerPayload, x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    act = payload.action.lower().strip()
    
    if act == "lock":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return {"status": "ok", "message": "Workstation locked successfully."}
    elif act == "sleep":
        subprocess.run(["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"], check=False)
        return {"status": "ok", "message": "PC entered sleep mode."}
    elif act == "hibernate":
        subprocess.run(["shutdown", "/h"], check=False)
        return {"status": "ok", "message": "PC entered hibernation."}
    elif act == "restart":
        subprocess.run(["shutdown", "/r", "/t", "5"], check=False)
        return {"status": "ok", "message": "PC will restart in 5 seconds."}
    elif act in ("shutdown", "poweroff"):
        subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
        return {"status": "ok", "message": "PC will shut down in 5 seconds."}
    elif act in ("cancel", "abort"):
        subprocess.run(["shutdown", "/a"], check=False)
        return {"status": "ok", "message": "Scheduled shutdown/restart canceled."}
    return {"status": "error", "message": f"Unknown action '{act}'"}

class ExecPayload(BaseModel):
    command: str

@app.post("/exec")
def exec_cmd(payload: ExecPayload, x_pc_secret: Optional[str] = Header(None)):
    verify_secret(x_pc_secret)
    cmd = payload.command.strip()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=20
        )
        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "output": proc.stdout,
            "error": proc.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "output": "", "error": "Command timed out after 20s."}
    except Exception as e:
        return {"status": "error", "output": "", "error": str(e)}

if __name__ == "__main__":
    port = 8085
    print(f"""
============================================================
           WEDNESDAY PC COMPANION AGENT RUNNING             
============================================================
 [Port] http://0.0.0.0:{port}
 [Status] Ready for Remote Access from Telegram & Phone
 [Auth Key] {PC_SECRET}
============================================================
""")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
