import os
import subprocess
from pathlib import Path

def setup_startup():
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    shortcut_path = os.path.join(startup_dir, "WednesdayAI.lnk")
    vbs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "start_silent_background.vbs"))
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    ps_code = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{shortcut_path}')
$s.TargetPath = 'wscript.exe'
$s.Arguments = '"{vbs_path}"'
$s.WorkingDirectory = '{project_dir}'
$s.Description = 'Wednesday AI Voice Assistant'
$s.Save()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], check=True)
    if os.path.exists(shortcut_path):
        print(f"[Success] Wednesday AI registered in Windows Startup folder: {shortcut_path}")
    else:
        print("[Error] Failed to create shortcut.")

if __name__ == "__main__":
    setup_startup()
