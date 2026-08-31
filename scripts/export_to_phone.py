import os
import sys
import zipfile
import socket
import http.server
import socketserver
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_NAME = "wednesday_exact.zip"
ZIP_PATH = PROJECT_ROOT / ZIP_NAME

EXCLUDE_DIRS = {"venv", ".git", "__pycache__", ".venv", "env", "recordings"}
EXCLUDE_EXTS = {".pyc", ".mp4", ".wav", ".log", ".tmp"}

def create_project_zip() -> Path:
    print(f"[*] Packaging exact project state from {PROJECT_ROOT}...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in EXCLUDE_EXTS or file == ZIP_NAME:
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(PROJECT_ROOT)
                zipf.write(full_path, rel_path)
    print(f"[+] Archive created successfully ({os.path.getsize(ZIP_PATH) / (1024*1024):.2f} MB): {ZIP_PATH.name}")
    return ZIP_PATH

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class SingleFileHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)
    def log_message(self, format, *args):
        print(f"[Phone Transfer] {args[0]} - {args[1]}")

def serve_zip(port: int = 8090):
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{port}/{ZIP_NAME}"
    
    print("\n" + "=" * 65)
    print("      WEDNESDAY AI - INSTANT TABLET / PHONE TRANSFER SERVER     ")
    print("=" * 65)
    print(f" [PC IP Address]  : {local_ip}")
    print(f" [Archive File]   : {ZIP_NAME}")
    print(f" [Direct URL]     : {url}")
    print("=" * 65)
    print("\n📱 RUN THIS SINGLE COMMAND IN TERMUX ON YOUR TABLET:\n")
    termux_cmd = f"pkg install -y curl unzip && curl -o wednesday.zip {url} && unzip -o wednesday.zip -d wednesday && cd wednesday && chmod +x *.sh && ./setup_termux.sh"
    print(f"  {termux_cmd}\n")
    print("=" * 65)
    print("Waiting for your tablet to download the project... (Press Ctrl+C when done)\n")

    handler = SingleFileHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Transfer server stopped.")
        finally:
            if ZIP_PATH.exists():
                try:
                    os.remove(ZIP_PATH)
                    print("[+] Cleaned up temporary zip archive.")
                except Exception:
                    pass

if __name__ == "__main__":
    create_project_zip()
    port = 8090
    serve_zip(port)
