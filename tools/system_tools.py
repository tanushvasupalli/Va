import os
import io
import re
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

def get_current_time_and_date() -> str:
    """Returns the current local time, day of the week, and date."""
    now = datetime.now()
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y.")

# =========================================================================
# COMPREHENSIVE PROTOCOLS & URLS FOR INSTANT BROWSER & DESKTOP LAUNCH
# =========================================================================
APP_PROTOCOL_MAP = {
    # Microsoft Office Suite
    "word": "ms-word:",
    "ms word": "ms-word:",
    "microsoft word": "ms-word:",
    "winword": "ms-word:",
    "excel": "ms-excel:",
    "ms excel": "ms-excel:",
    "microsoft excel": "ms-excel:",
    "powerpoint": "ms-powerpoint:",
    "ppt": "ms-powerpoint:",
    "ms powerpoint": "ms-powerpoint:",
    "microsoft powerpoint": "ms-powerpoint:",
    "onenote": "onenote:",
    "ms onenote": "onenote:",
    "microsoft onenote": "onenote:",
    "outlook": "mailto:",
    "ms outlook": "mailto:",
    "microsoft outlook": "mailto:",

    # Windows Native Apps (Windows Protocol Handlers)
    "calculator": "calculator:",
    "calc": "calculator:",
    "notepad": "ms-notepad:",
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "spotify": "spotify:",
    "whatsapp": "whatsapp:",
    "camera": "microsoft.windows.camera:",
    "snipping tool": "ms-screenclip:",
    "snip": "ms-screenclip:",
    "store": "ms-windows-store:",
    "microsoft store": "ms-windows-store:",
    "paint": "ms-paint:",
    "edge": "microsoft-edge:",
    "mail": "mailto:",
    "photos": "ms-photos:",
    "clock": "ms-clock:",
    "alarms": "ms-clock:",

    # Top Websites & Web Services
    "youtube": "https://www.youtube.com",
    "yt": "https://www.youtube.com",
    "instagram": "https://www.instagram.com",
    "insta": "https://www.instagram.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://www.x.com",
    "x": "https://www.x.com",
    "gmail": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "fb": "https://www.facebook.com",
    "netflix": "https://www.netflix.com",
    "discord": "https://discord.com/app",
    "chatgpt": "https://chatgpt.com",
    "linkedin": "https://www.linkedin.com",
    "twitch": "https://www.twitch.tv",
    "tiktok": "https://www.tiktok.com",
    "pinterest": "https://www.pinterest.com",
    "amazon": "https://www.amazon.com",
    "file explorer": "file:///C:/Users/tanus/Documents",
    "files": "file:///C:/Users/tanus/Documents",
    "explorer": "file:///C:/Users/tanus/Documents",
}

# Windows Shell Execution Fallbacks
DESKTOP_EXE_COMMANDS = {
    # Microsoft Office Apps
    "word": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE'",
        "explorer.exe ms-word:"
    ],
    "ms word": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE'",
        "explorer.exe ms-word:"
    ],
    "microsoft word": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE'",
        "explorer.exe ms-word:"
    ],
    "winword": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE'"
    ],
    "excel": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE'",
        "explorer.exe ms-excel:"
    ],
    "ms excel": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE'",
        "explorer.exe ms-excel:"
    ],
    "microsoft excel": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE'"
    ],
    "powerpoint": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE'",
        "explorer.exe ms-powerpoint:"
    ],
    "ppt": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE'",
        "explorer.exe ms-powerpoint:"
    ],
    "ms powerpoint": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE'"
    ],
    "microsoft powerpoint": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE'"
    ],
    "onenote": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\ONENOTE.EXE'",
        "explorer.exe onenote:"
    ],
    "ms onenote": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\ONENOTE.EXE'"
    ],
    "microsoft onenote": [
        "powershell -NoProfile -Command Start-Process 'C:\\Program Files\\Microsoft Office\\root\\Office16\\ONENOTE.EXE'"
    ],

    # Windows Apps & Tools
    "notepad": [r"explorer.exe shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App", "ms-notepad:"],
    "calculator": ["calculator:", r"explorer.exe shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"],
    "calc": ["calculator:"],
    "paint": [r"explorer.exe shell:AppsFolder\Microsoft.Paint_8wekyb3d8bbwe!App", "mspaint.exe"],
    "terminal": [r"explorer.exe shell:AppsFolder\Microsoft.WindowsTerminal_8wekyb3d8bbwe!App", "wt.exe"],
    "cmd": ["explorer.exe cmd.exe", "cmd.exe"],
    "command prompt": ["explorer.exe cmd.exe"],
    "powershell": ["powershell.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "task manager": ["powershell.exe -NoProfile -Command Start-Process taskmgr.exe"],
    "taskmgr": ["powershell.exe -NoProfile -Command Start-Process taskmgr.exe"],
    "settings": ["explorer.exe ms-settings:"],
    "chrome": [r"explorer.exe shell:AppsFolder\Chrome", "chrome.exe"],
    "google chrome": [r"explorer.exe shell:AppsFolder\Chrome"],
    "spotify": [r'powershell.exe -NoProfile -Command Start-Process "C:\Users\tanus\AppData\Roaming\Spotify\Spotify.exe"', "spotify:"],
    "whatsapp": [r"explorer.exe shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App", "whatsapp:"],
    "telegram": [r"explorer.exe shell:AppsFolder\TelegramMessengerLLP.TelegramDesktop_t4vj0pshhgkwm!Telegram"],
    "obsidian": [r"explorer.exe shell:AppsFolder\md.obsidian"],
    "vscode": ["powershell.exe -NoProfile -Command Start-Process code", "code"],
    "vs code": ["powershell.exe -NoProfile -Command Start-Process code"],
    "code": ["powershell.exe -NoProfile -Command Start-Process code"],
    "camera": [r"explorer.exe shell:AppsFolder\Microsoft.WindowsCamera_8wekyb3d8bbwe!App", "microsoft.windows.camera:"],
    "snipping tool": [r"explorer.exe shell:AppsFolder\Microsoft.ScreenSketch_8wekyb3d8bbwe!App", "ms-screenclip:"],
}

def resolve_target_url(target: str) -> str | None:
    """
    Extracts the destination URL or protocol handler for any website or application.
    """
    if not target:
        return None
    target_clean = target.lower().strip()

    # Greetings or casual text
    greetings = ["hi", "hello", "hey", "good morning", "good evening", "how are you", "yo", "sup", "what's up", "help", "thanks", "thank you", "bye"]
    if target_clean in greetings:
        return None

    # Direct URLs
    if target_clean.startswith("http://") or target_clean.startswith("https://") or target_clean.startswith("file:///"):
        return target_clean
    if target_clean.startswith("www."):
        return f"https://{target_clean}"

    open_prefix_match = re.match(r"^(?:please\s+|can\s+you\s+|would\s+you\s+)?(?:open|launch|start|go\s+to|visit|show\s+me)\s+([a-zA-Z0-9_\-\.\s]+)$", target_clean)
    if not open_prefix_match:
        return None

    clean_name = open_prefix_match.group(1).strip()
    clean_name = re.sub(r"\s+(app|application|on my pc|on my computer|in browser|website)$", "", clean_name).strip()

    # Informational search keywords guard
    search_keywords = ["find", "search", "what", "who", "why", "when", "latest", "video", "channel", "how", "tell me", "news"]
    if any(k in clean_name for k in search_keywords):
        return None

    # Check exact dictionary matches
    for app_key, url_or_proto in APP_PROTOCOL_MAP.items():
        if app_key == clean_name:
            return url_or_proto

    for app_key, url_or_proto in APP_PROTOCOL_MAP.items():
        if app_key in clean_name:
            return url_or_proto

    if any(clean_name.endswith(tld) for tld in [".com", ".org", ".net", ".io", ".ai", ".tv", ".app", ".dev"]):
        return f"https://{clean_name}"

    return None

def launch_app_native(cmd: str) -> bool:
    """Launches an application locally via Windows shell commands."""
    try:
        if cmd.startswith("http://") or cmd.startswith("https://"):
            webbrowser.open_new_tab(cmd)
            return True
        elif cmd.endswith(":"):
            subprocess.Popen(f'explorer.exe "{cmd}"', shell=True)
            return True
        else:
            subprocess.Popen(cmd, shell=True)
            return True
    except Exception:
        return False

def open_application_or_site(target: str) -> str:
    """
    Opens applications (Word, Excel, PowerPoint, Calculator, Notepad, Spotify, WhatsApp, VS Code, Chrome, etc.)
    or websites.
    """
    if not target or not target.strip():
        return "No application or website specified."

    target_clean = target.lower().strip()
    target_clean = re.sub(r"^(?:please\s+|can\s+you\s+|would\s+you\s+)?(?:open|launch|start|go\s+to|show\s+me)\s+", "", target_clean).strip()
    target_clean = re.sub(r"\s+(app|application|on my pc|on my computer|in browser|website)$", "", target_clean).strip()
    target_clean = target_clean.replace("\"", "").replace("'", "").strip()

    # 1. Check Desktop Applications (Exact Match)
    for app_key, cmd_list in DESKTOP_EXE_COMMANDS.items():
        if app_key == target_clean:
            for cmd in cmd_list:
                launch_app_native(cmd)
            return f"Opening {app_key.capitalize()} on your PC."

    # 2. Check Desktop Applications (Substring Match)
    for app_key, cmd_list in DESKTOP_EXE_COMMANDS.items():
        if app_key in target_clean or target_clean in app_key:
            for cmd in cmd_list:
                launch_app_native(cmd)
            return f"Opening {app_key.capitalize()} on your PC."

    # 3. Check Protocol & Web Services
    url = resolve_target_url("open " + target_clean)
    if url:
        launch_app_native(url)
        return f"Opening {target_clean.capitalize()} for you."

    # 4. Fallback
    launch_app_native(f"explorer.exe {target_clean}")
    return f"Opening {target_clean.capitalize()} on your PC."

# =========================================================================
# SYSTEM POWER & STATE MANAGEMENT (SECURED WITH PIN AUTHENTICATION)
# =========================================================================

def execute_raw_power_action(action: str, delay_seconds: int = 5) -> str:
    """Executes the raw Windows power action after security verification."""
    act = action.lower().strip()
    try:
        if act in ("shutdown", "poweroff"):
            subprocess.Popen(f"shutdown /s /f /t {int(delay_seconds)}", shell=True)
            return f"PIN verified. Shutting down your PC in {delay_seconds} seconds. Goodbye!"
        elif act in ("restart", "reboot"):
            subprocess.Popen(f"shutdown /r /f /t {int(delay_seconds)}", shell=True)
            return f"PIN verified. Restarting your PC in {delay_seconds} seconds."
        elif act == "sleep":
            import ctypes
            res = ctypes.windll.powrprof.SetSuspendState(0, 0, 0)
            if not res:
                subprocess.Popen(
                    'powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)"',
                    shell=True
                )
            return "PIN verified. Putting your laptop to sleep now."
        elif act == "hibernate":
            subprocess.Popen("shutdown /h", shell=True)
            return "PIN verified. Putting your laptop into hibernation now."
        elif act == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Locking the Windows workstation."
        elif act in ("cancel", "abort"):
            subprocess.Popen("shutdown /a", shell=True)
            return "Pending shutdown or restart has been cancelled."
        return f"Unknown power action '{act}'."
    except Exception as e:
        return f"Failed to execute power action: {e}"

def shutdown_system(delay_seconds: int = 5, pin: str = "") -> str:
    """Schedules a Windows system shutdown. Requires security PIN."""
    from core.security import verify_power_password
    if not pin or not verify_power_password(pin):
        return "Authentication required. Please provide your 4-digit security PIN to shut down your PC."
    return execute_raw_power_action("shutdown", delay_seconds)

def restart_system(delay_seconds: int = 5, pin: str = "") -> str:
    """Schedules a Windows system restart. Requires security PIN."""
    from core.security import verify_power_password
    if not pin or not verify_power_password(pin):
        return "Authentication required. Please provide your 4-digit security PIN to restart your PC."
    return execute_raw_power_action("restart", delay_seconds)

def sleep_system(pin: str = "") -> str:
    """Puts Windows PC into Sleep mode. Requires security PIN."""
    from core.security import verify_power_password
    if not pin or not verify_power_password(pin):
        return "Authentication required. Please provide your 4-digit security PIN to put your laptop to sleep."
    return execute_raw_power_action("sleep")

def hibernate_system(pin: str = "") -> str:
    """Puts Windows PC into Hibernation mode. Requires security PIN."""
    from core.security import verify_power_password
    if not pin or not verify_power_password(pin):
        return "Authentication required. Please provide your 4-digit security PIN to hibernate your PC."
    return execute_raw_power_action("hibernate")

def lock_system() -> str:
    """Locks the Windows workstation immediately (does not require PIN)."""
    return execute_raw_power_action("lock")

def cancel_shutdown() -> str:
    """Cancels any pending Windows shutdown or restart."""
    return execute_raw_power_action("cancel")

def change_power_pin(current_pin: str, new_pin: str) -> str:
    """Updates the 4-digit security PIN used for power actions."""
    from core.security import set_power_password
    ok, msg = set_power_password(current_pin, new_pin)
    return msg

# =========================================================================
# SCREENSHOT CAPTURE ENGINE
# =========================================================================

def capture_desktop_screenshot(save_path: str = "") -> tuple[bytes | None, str]:
    """
    Captures a full-resolution screenshot of the active Windows desktop across all monitors.
    Uses Win32 OpenInputDesktop and DISPLAY DC to ensure active desktop pixel capture
    even when running in background threads or services.
    Returns:
        tuple[bytes | None, str]: (raw PNG bytes or None, metadata message)
    """
    img = None
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import Image

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        # 1. Ensure Per-Monitor DPI Awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

        # 2. Attach thread to active interactive input desktop
        GENERIC_ALL = 0x10000000
        hdesk = user32.OpenInputDesktop(0, False, GENERIC_ALL)
        if hdesk:
            user32.SetThreadDesktop(hdesk)

        # 3. Create device context for active display
        hdc_screen = gdi32.CreateDCA(b"DISPLAY", None, None, None)
        if not hdc_screen:
            hdc_screen = user32.GetDC(0)

        # 4. Determine screen coordinates covering all virtual monitors
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN

        if width <= 0 or height <= 0:
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            x = 0
            y = 0

        # 5. Create compatible memory DC and bitmap
        hmem_dc = gdi32.CreateCompatibleDC(hdc_screen)
        hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        old_bmp = gdi32.SelectObject(hmem_dc, hbitmap)

        # 6. Copy screen bits with SRCCOPY and CAPTUREBLT (captures layered & translucent windows)
        SRCCOPY = 0x00CC0020
        CAPTUREBLT = 0x40000000
        gdi32.BitBlt(hmem_dc, 0, 0, width, height, hdc_screen, x, y, SRCCOPY | CAPTUREBLT)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG), ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(hmem_dc, hbitmap, 0, height, buffer, ctypes.byref(bmi), 0)

        # 7. Release Windows GDI handles
        gdi32.SelectObject(hmem_dc, old_bmp)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hmem_dc)
        if hdc_screen:
            gdi32.DeleteDC(hdc_screen)
        if hdesk:
            user32.CloseDesktop(hdesk)

        # 8. Convert BGRA raw buffer to PIL RGB Image
        img = Image.frombuffer('RGBA', (width, height), buffer, 'raw', 'BGRA', 0, 1).convert('RGB')
    except Exception as e:
        # Fallback to PIL ImageGrab if available
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True).convert('RGB')
        except Exception:
            return None, f"Failed to capture desktop screenshot: {e}"

    if img is None:
        return None, "Screenshot engine could not capture the desktop."

    try:
        width, height = img.size
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()

        timestamp_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        meta = f"Screenshot ({width}x{height}) captured at {timestamp_str}"

        if save_path:
            p = Path(save_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(p))
            meta += f", saved to {p}"

        return png_bytes, meta
    except Exception as e:
        return None, f"Failed to encode screenshot: {e}"


