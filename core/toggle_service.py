import os
import sys
import time
import subprocess
import psutil
import winsound
from pathlib import Path
from typing import Tuple, List

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHONW_EXE = BASE_DIR / "venv" / "Scripts" / "pythonw.exe"
PYTHON_EXE = BASE_DIR / "venv" / "Scripts" / "python.exe"
BOT_SCRIPT = BASE_DIR / "core" / "telegram_bot.py"

def play_sound_cue(state_on: bool):
    """Plays an auditory feedback chime for state changes."""
    try:
        if state_on:
            winsound.Beep(1200, 120)
            winsound.Beep(1800, 180)
        else:
            winsound.Beep(1800, 120)
            winsound.Beep(900, 200)
    except Exception:
        pass

def get_running_bot_pids() -> List[int]:
    """Finds PIDs of running Wednesday Telegram bot processes."""
    pids = []
    current_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            name = proc.info['name'] or ''
            if 'python' in name.lower():
                cmdline = proc.info['cmdline'] or []
                if len(cmdline) >= 2:
                    script_arg = cmdline[1].lower().replace('/', '\\')
                    if script_arg.endswith('telegram_bot.py'):
                        pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return pids

def is_wednesday_running() -> bool:
    """Returns True if Wednesday AI bot is actively running in background."""
    return len(get_running_bot_pids()) > 0

def start_wednesday() -> Tuple[bool, str]:
    """Starts the Wednesday AI background bot process silently."""
    if is_wednesday_running():
        return True, "[ONLINE] Wednesday AI is already active and running."

    exe = str(PYTHONW_EXE if PYTHONW_EXE.exists() else PYTHON_EXE)
    script = str(BOT_SCRIPT)

    try:
        # DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)
        flags = (0x00000008 | 0x00000200 | 0x08000000) if os.name == 'nt' else 0
        subprocess.Popen(
            [exe, script],
            cwd=str(BASE_DIR),
            creationflags=flags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.0)
        play_sound_cue(state_on=True)
        return True, "[ONLINE] Wednesday AI Activated."
    except Exception as e:
        return False, f"Failed to start Wednesday AI: {e}"

def stop_wednesday() -> Tuple[bool, str]:
    """Gracefully terminates all active Wednesday AI bot processes."""
    pids = get_running_bot_pids()
    if not pids:
        return True, "[OFFLINE] Wednesday AI is already stopped."

    terminated_count = 0
    for pid in pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
            terminated_count += 1
        except Exception:
            pass

    time.sleep(0.5)
    # Force kill any lingering processes
    for pid in pids:
        try:
            p = psutil.Process(pid)
            if p.is_running():
                p.kill()
        except Exception:
            pass

    play_sound_cue(state_on=False)
    return True, f"[OFFLINE] Wednesday AI Deactivated (Stopped {terminated_count} process{'es' if terminated_count != 1 else ''})."

def toggle_wednesday() -> Tuple[bool, str]:
    """Toggles Wednesday AI on or off based on current state."""
    if is_wednesday_running():
        return stop_wednesday()
    else:
        return start_wednesday()

if __name__ == "__main__":
    ok, message = toggle_wednesday()
    print(message)
