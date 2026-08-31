import time
import ctypes
from typing import Optional

try:
    if hasattr(ctypes, "windll"):
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except Exception:
    pyautogui = None

def click_coordinates(x: int, y: int, click_type: str = "single") -> str:
    """
    Moves mouse cursor to specific (x, y) coordinates and performs a click.
    Click types: single, double, right, middle
    """
    if pyautogui is None:
        return "UI control (mouse/keyboard) is only available on desktop environments."
    try:
        pyautogui.moveTo(x, y, duration=0.25)
        act = click_type.lower().strip()
        
        if act in ("double", "double_click", "dbl"):
            pyautogui.doubleClick(x, y)
            return f"Double-clicked at ({x}, {y})."
        elif act in ("right", "right_click"):
            pyautogui.rightClick(x, y)
            return f"Right-clicked at ({x}, {y})."
        elif act in ("middle", "middle_click"):
            pyautogui.middleClick(x, y)
            return f"Middle-clicked at ({x}, {y})."
        else:
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})."
    except Exception as e:
        return f"Failed to click at ({x}, {y}): {e}"

def click_screen_item(target_description: str, click_type: str = "single") -> str:
    """
    Uses AI Vision to find a named icon, button, menu, or text on screen,
    moves the cursor to it, and performs a click.
    """
    from tools.vision_tools import find_ui_element_coordinates
    coords, msg = find_ui_element_coordinates(target_description)
    if not coords:
        return msg

    x, y = coords
    res = click_coordinates(x, y, click_type)
    return f"{msg} -> {res}"

def type_text_into_ui(text: str, press_enter: bool = False) -> str:
    """
    Types text into the currently active window/input field on the laptop.
    Optionally presses Enter after typing.
    """
    if pyautogui is None:
        return "UI control (mouse/keyboard) is only available on desktop environments."
    try:
        # If clipboard is preferred for unicode/special characters:
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.05)
        
        if press_enter:
            pyautogui.press("enter")
            return f"Typed: \"{text}\" and pressed Enter."
        return f"Typed: \"{text}\"."
    except Exception as e:
        try:
            pyautogui.write(text, interval=0.02)
            if press_enter:
                pyautogui.press("enter")
            return f"Typed: \"{text}\"."
        except Exception as e2:
            return f"Failed to type text: {e2}"

def press_hotkey(hotkey_str: str) -> str:
    """
    Simulates pressing a keyboard key or shortcut combination.
    Examples: 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+d', 'enter', 'esc', 'space', 'f5'
    """
    if pyautogui is None:
        return "UI control (mouse/keyboard) is only available on desktop environments."
    try:
        clean = hotkey_str.lower().strip()
        parts = [p.strip() for p in clean.replace("-", "+").split("+") if p.strip()]
        
        # Map common names
        mapped_parts = []
        for p in parts:
            if p in ("win", "windows", "super", "cmd"):
                mapped_parts.append("win")
            elif p in ("control", "ctrl"):
                mapped_parts.append("ctrl")
            elif p in ("alternate", "alt"):
                mapped_parts.append("alt")
            elif p in ("return", "enter"):
                mapped_parts.append("enter")
            elif p in ("escape", "esc"):
                mapped_parts.append("esc")
            else:
                mapped_parts.append(p)

        if len(mapped_parts) == 1:
            pyautogui.press(mapped_parts[0])
            return f"Pressed key: `{mapped_parts[0]}`"
        else:
            pyautogui.hotkey(*mapped_parts)
            return f"Pressed hotkey combination: `{' + '.join(mapped_parts)}`"
    except Exception as e:
        return f"Failed to press hotkey '{hotkey_str}': {e}"

def scroll_screen(clicks: int = -3) -> str:
    """
    Scrolls the mouse wheel up (positive integer) or down (negative integer).
    """
    if pyautogui is None:
        return "UI control (mouse/keyboard) is only available on desktop environments."
    try:
        pyautogui.scroll(clicks * 100)
        direction = "down" if clicks < 0 else "up"
        return f"Scrolled {direction} ({abs(clicks)} units)."
    except Exception as e:
        return f"Failed to scroll screen: {e}"

def move_mouse(x: int, y: int) -> str:
    """Moves the mouse cursor to (x, y) coordinates without clicking."""
    if pyautogui is None:
        return "UI control (mouse/keyboard) is only available on desktop environments."
    try:
        pyautogui.moveTo(x, y, duration=0.3)
        return f"Mouse moved to ({x}, {y})."
    except Exception as e:
        return f"Failed to move mouse: {e}"
