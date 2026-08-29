import os
import re
import subprocess
import webbrowser
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
# SYSTEM POWER & STATE MANAGEMENT
# =========================================================================
def shutdown_system(delay_seconds: int = 5) -> str:
    """Schedules a Windows system shutdown."""
    try:
        subprocess.Popen(f"shutdown /s /f /t {int(delay_seconds)}", shell=True)
        return f"Shutting down your PC in {delay_seconds} seconds. Goodbye!"
    except Exception as e:
        return f"Failed to initiate shutdown: {e}"

def restart_system(delay_seconds: int = 5) -> str:
    """Schedules a Windows system restart."""
    try:
        subprocess.Popen(f"shutdown /r /f /t {int(delay_seconds)}", shell=True)
        return f"Restarting your PC in {delay_seconds} seconds."
    except Exception as e:
        return f"Failed to initiate restart: {e}"

def sleep_system() -> str:
    """Puts Windows PC into Sleep / Standby mode."""
    try:
        import ctypes
        # powrprof.dll: SetSuspendState(bHibernate, bForce, bWakeupEventsDisabled)
        # bHibernate = 0 for Sleep/Suspend
        res = ctypes.windll.powrprof.SetSuspendState(0, 0, 0)
        if not res:
            subprocess.Popen(
                'powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)"',
                shell=True
            )
        return "Putting the computer to sleep now."
    except Exception as e:
        return f"Failed to put system to sleep: {e}"

def hibernate_system() -> str:
    """Puts Windows PC into Hibernation mode."""
    try:
        subprocess.Popen("shutdown /h", shell=True)
        return "Putting the computer into hibernation now."
    except Exception as e:
        return f"Failed to hibernate: {e}"

def lock_system() -> str:
    """Locks the Windows workstation immediately."""
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Locking the Windows workstation."
    except Exception as e:
        return f"Failed to lock workstation: {e}"

def cancel_shutdown() -> str:
    """Cancels any pending Windows shutdown or restart."""
    try:
        subprocess.Popen("shutdown /a", shell=True)
        return "Pending shutdown or restart has been cancelled."
    except Exception as e:
        return f"Failed to cancel shutdown: {e}"

