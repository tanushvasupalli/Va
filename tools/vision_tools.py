import io
import re
import json
from typing import Optional, Tuple, Dict, Any
from PIL import Image
from google import genai
from google.genai import types
import config
from tools.system_tools import capture_desktop_screenshot

def _get_gemini_client() -> Optional[genai.Client]:
    api_key = getattr(config, "GEMINI_API_KEY", "") or ""
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def get_screen_view(question_or_prompt: Optional[str] = None) -> str:
    """
    Captures a real-time screenshot of the laptop desktop and uses Gemini Vision
    to analyze what is currently displayed, open applications, errors, or answer specific visual questions.
    """
    client = _get_gemini_client()
    if not client:
        return "Gemini Vision is not configured (GEMINI_API_KEY missing in .env)."

    img_bytes, msg = capture_desktop_screenshot()
    if not img_bytes:
        return f"Failed to capture screen view: {msg}"

    try:
        img = Image.open(io.BytesIO(img_bytes))
        width, height = img.size

        prompt = question_or_prompt.strip() if question_or_prompt and question_or_prompt.strip() else (
            "Analyze this desktop screen (resolution {w}x{h}). "
            "Describe the active windows, open software, main tasks or code visible, "
            "and any notifications, popups, or status bars."
        ).format(w=width, h=height)

        vision_prompt = (
            f"You are the visual cortex of Wednesday AI assistant. The user's screen resolution is {width}x{height}.\n"
            f"User Prompt: {prompt}\n\n"
            "Provide a concise, clear, and direct visual summary. Highlight key UI items, active applications, and text."
        )

        response = client.models.generate_content(
            model=getattr(config, "GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                vision_prompt
            ]
        )

        if response and response.text:
            return response.text.strip()
        return "Screen captured, but no visual description was generated."

    except Exception as e:
        # Fallback to secondary model if primary fails
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    f"Analyze this desktop screen and summarize what is visible: {question_or_prompt or 'Overview'}"
                ]
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e2:
            return f"Vision analysis failed: {e2}"
        return f"Vision analysis error: {e}"

def find_ui_element_coordinates(target_description: str) -> Tuple[Optional[Tuple[int, int]], str]:
    """
    Uses Gemini Vision to locate the pixel coordinates (x, y) of a named icon, button,
    menu, text, or UI element on the laptop screen.
    Returns:
        ((x, y), explanation_message)
    """
    client = _get_gemini_client()
    if not client:
        return None, "Gemini Vision is not configured (GEMINI_API_KEY missing)."

    img_bytes, msg = capture_desktop_screenshot()
    if not img_bytes:
        return None, f"Failed to capture screen: {msg}"

    try:
        img = Image.open(io.BytesIO(img_bytes))
        width, height = img.size

        spatial_prompt = (
            f"You are an expert UI automation vision system. Screen resolution: {width}x{height}.\n"
            f"Target to locate: \"{target_description}\"\n\n"
            "Locate the exact center of this requested UI element on the screen.\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "{\n"
            "  \"found\": true,\n"
            "  \"x\": 500,\n"
            "  \"y\": 300,\n"
            "  \"element_name\": \"Google Chrome Icon\",\n"
            "  \"description\": \"Blue and red Chrome icon on the bottom taskbar\"\n"
            "}\n"
            "If the element is NOT visible on the screen, respond with:\n"
            "{\n"
            "  \"found\": false,\n"
            "  \"reason\": \"Could not find target on the active screen\"\n"
            "}"
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                spatial_prompt
            ]
        )

        text = response.text.strip() if response and response.text else ""
        
        # Parse JSON from markdown code block or raw string
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            if data.get("found"):
                x = int(data.get("x", 0))
                y = int(data.get("y", 0))
                desc = data.get("description", target_description)
                
                # Bounds check
                x = max(0, min(x, width - 1))
                y = max(0, min(y, height - 1))
                return (x, y), f"Located '{target_description}' at ({x}, {y}) [{desc}]."
            else:
                reason = data.get("reason", "Target element not found on screen.")
                return None, f"Element '{target_description}' was not found: {reason}"

        return None, f"Could not parse element coordinates from Vision response: {text[:200]}"

    except Exception as e:
        return None, f"Vision localization error: {e}"
