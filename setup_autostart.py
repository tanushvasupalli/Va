import os
import sys
import subprocess
from pathlib import Path

STARTUP_DIR = Path(os.getenv("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
PROJECT_DIR = Path(__file__).resolve().parent
TARGET_SHORTCUT = STARTUP_DIR / "WednesdayAI.lnk"
OBSOLETE_VBS = STARTUP_DIR / "WednesdayAI.vbs"
VBS_SCRIPT = PROJECT_DIR / "scripts" / "start_silent_background.vbs"

def enable_autostart() -> bool:
    """Adds Wednesday AI background service to Windows Startup folder."""
    try:
        STARTUP_DIR.mkdir(parents=True, exist_ok=True)

        # Remove any obsolete/broken VBS file in the startup folder
        if OBSOLETE_VBS.exists():
            OBSOLETE_VBS.unlink()

        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{str(TARGET_SHORTCUT)}'); "
            f"$s.TargetPath = 'wscript.exe'; "
            f"$s.Arguments = '\"{str(VBS_SCRIPT)}\"'; "
            f"$s.WorkingDirectory = '{str(PROJECT_DIR)}'; "
            f"$s.Description = 'Wednesday AI Voice Assistant Background Service'; "
            f"$s.Save()"
        )

        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            check=True,
            capture_output=True,
            text=True
        )

        if TARGET_SHORTCUT.exists():
            print("==================================================")
            print(" [SUCCESS] Auto-start on boot is now ENABLED!")
            print(" Wednesday will start automatically in the background whenever your PC boots.")
            print(f" Startup Shortcut:  {TARGET_SHORTCUT}")
            print(f" Target Script:     {VBS_SCRIPT}")
            print(f" Working Directory: {PROJECT_DIR}")
            print("==================================================")
            return True
        else:
            print("[Error] Failed to verify created shortcut in Startup folder.")
            return False
    except Exception as e:
        print(f"[Error] Failed to enable autostart: {e}")
        return False

def disable_autostart() -> bool:
    """Removes Wednesday from Windows Startup folder."""
    try:
        removed = False
        if TARGET_SHORTCUT.exists():
            TARGET_SHORTCUT.unlink()
            removed = True
        if OBSOLETE_VBS.exists():
            OBSOLETE_VBS.unlink()
            removed = True

        if removed:
            print("==================================================")
            print(" [SUCCESS] Auto-start on boot is now DISABLED.")
            print("==================================================")
        else:
            print("Auto-start was not enabled.")
        return True
    except Exception as e:
        print(f"[Error] Failed to disable autostart: {e}")
        return False

def status_autostart() -> bool:
    """Checks and reports whether autostart is properly configured."""
    print("==================================================")
    print("       WEDNESDAY AI - AUTOSTART STATUS CHECK      ")
    print("==================================================")

    if not TARGET_SHORTCUT.exists():
        print(" [Status] Auto-start is currently: DISABLED")
        print(" To enable auto-start, run: python setup_autostart.py")
        print("==================================================")
        return False

    print(" [Status] Auto-start is currently: ENABLED")
    print(f" [Shortcut Path]: {TARGET_SHORTCUT}")

    ps_cmd = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{str(TARGET_SHORTCUT)}'); "
        f"Write-Host '  TargetPath:       ' $s.TargetPath; "
        f"Write-Host '  Arguments:        ' $s.Arguments; "
        f"Write-Host '  WorkingDirectory: ' $s.WorkingDirectory"
    )
    res = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
        capture_output=True,
        text=True
    )
    if res.stdout:
        print(res.stdout.strip())
    print("==================================================")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["disable", "--disable", "remove"]:
            disable_autostart()
        elif arg in ["status", "--status", "check"]:
            status_autostart()
        else:
            enable_autostart()
    else:
        enable_autostart()
