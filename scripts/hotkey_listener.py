import os
import sys
import time
import datetime
from pathlib import Path
import ctypes
from ctypes import wintypes

# Guard against NoneType stdout/stderr when running silently via pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.toggle_service import toggle_wednesday

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LOG_FILE = BASE_DIR / "data" / "hotkey.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log_msg(msg: str):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def attach_to_input_desktop():
    """Attaches the current thread to the interactive Windows input desktop."""
    try:
        DESKTOP_ALL = 0x01FF
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            return hdesk
    except Exception as e:
        log_msg(f"Failed to attach thread desktop: {e}")
    return None

def ensure_single_instance():
    """Ensures only one instance of the hotkey listener runs at a time."""
    mutex_name = "WednesdayAI_GlobalHotkey_DesktopAttached_Mutex"
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        log_msg("Another hotkey listener instance is already running. Exiting duplicate.")
        sys.exit(0)
    return mutex

# Virtual Key Codes
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_MENU = 0x12       # Alt key
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_SHIFT = 0x10
VK_OEM_2 = 0xBF      # Main keyboard '/?' key
VK_DIVIDE = 0x6F     # Numpad '/' key
VK_W = 0x57          # 'W' key

def is_key_down(vk: int) -> bool:
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

def run_hotkey_listener():
    """Continuously monitors for physical Ctrl + / (and Ctrl + Alt + W) with desktop attachment."""
    mutex = ensure_single_instance()
    attach_to_input_desktop()

    log_msg("=" * 60)
    log_msg("Wednesday AI Desktop-Attached Hotkey Daemon Online")
    log_msg("Active Shortcuts: [ Ctrl + / ], [ Ctrl + Alt + W ], [ Alt + / ]")
    log_msg("=" * 60)

    last_trigger = 0.0
    was_triggered = False
    loop_count = 0

    while True:
        try:
            # Re-verify desktop attachment periodically every 5 seconds (200 ticks)
            loop_count += 1
            if loop_count % 200 == 0:
                attach_to_input_desktop()

            ctrl = is_key_down(VK_CONTROL) or is_key_down(VK_LCONTROL) or is_key_down(VK_RCONTROL)
            alt = is_key_down(VK_MENU) or is_key_down(VK_LMENU) or is_key_down(VK_RMENU)
            slash = is_key_down(VK_OEM_2) or is_key_down(VK_DIVIDE)
            w_key = is_key_down(VK_W)

            # Trigger condition 1: Ctrl + / (standard)
            # Trigger condition 2: Ctrl + Alt + W (failsafe when inside IDE)
            # Trigger condition 3: Alt + /
            combo_active = (ctrl and slash) or (ctrl and alt and w_key) or (alt and slash)

            if combo_active:
                now = time.time()
                if not was_triggered and (now - last_trigger > 0.8):
                    was_triggered = True
                    last_trigger = now
                    combo_name = "Ctrl + /" if (ctrl and slash) else ("Ctrl + Alt + W" if (ctrl and alt and w_key) else "Alt + /")
                    log_msg(f">>> GLOBAL HOTKEY [{combo_name}] TRIGGERED! <<<")
                    ok, status_msg = toggle_wednesday()
                    log_msg(f"Toggle Executed: {status_msg}")
            else:
                was_triggered = False

            time.sleep(0.025)  # 25ms interval = 40 checks/sec = 0.0% CPU
        except Exception as e:
            log_msg(f"Error in hotkey loop: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    run_hotkey_listener()
