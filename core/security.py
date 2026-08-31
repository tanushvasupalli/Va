import os
import re
import time
from typing import Optional, Dict, Any, Tuple
from core.storage import storage

DEFAULT_POWER_PIN = "2206"
PREF_KEY = "power_password"

# In-memory store for pending authentication states per session
# Format: session_id -> {"action": "shutdown"|"restart"|"sleep"|"hibernate", "timestamp": float, "delay_seconds": int}
_PENDING_POWER_ACTIONS: Dict[str, Dict[str, Any]] = {}
AUTH_TIMEOUT_SECONDS = 90  # Allow 90 seconds to provide the PIN

# Spoken number word mapping for voice input recognition
WORD_TO_DIGIT = {
    "zero": "0", "oh": "0", "one": "1", "won": "1", "two": "2", "to": "2", "too": "2",
    "three": "3", "four": "4", "for": "4", "fore": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "ate": "8", "nine": "9", "niner": "9"
}

def get_power_password() -> str:
    """Retrieves current power authentication PIN from database or defaults to 2206."""
    pin = storage.get_preference(PREF_KEY, DEFAULT_POWER_PIN)
    return str(pin).strip() if pin else DEFAULT_POWER_PIN

def verify_power_password(candidate_pin: str) -> bool:
    """Verifies a candidate PIN against the stored power password."""
    if not candidate_pin:
        return False
    current_pin = get_power_password()
    cleaned = str(candidate_pin).strip()
    return cleaned == current_pin

def set_power_password(current_pin: str, new_pin: str) -> Tuple[bool, str]:
    """Updates the power password after validating the current PIN."""
    current_stored = get_power_password()
    if str(current_pin).strip() != current_stored:
        return False, "Current security PIN is incorrect. Password change denied."
    
    new_clean = str(new_pin).strip()
    if not new_clean or len(new_clean) < 4:
        return False, "New security PIN must be at least 4 digits or characters."
    
    ok = storage.set_preference(PREF_KEY, new_clean)
    if ok:
        return True, f"Security PIN successfully updated to '{new_clean}'."
    return False, "Failed to persist new PIN to storage."

def extract_pin_from_text(text: str) -> Optional[str]:
    """
    Extracts 4 to 8 digit numeric PINs from text or transcribed speech.
    Supports both digit strings ('2206') and spoken words ('two two zero six').
    """
    if not text:
        return None
    
    # 1. Direct explicit pattern: "pin is 2206", "password 2206", "code 2206", "2206"
    match = re.search(r"(?:pin|password|passcode|code|auth)?\s*[:=]?\s*(\b\d{4,8}\b)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 2. Extract digit words sequence (e.g. "two two zero six")
    words = re.findall(r"\b\w+\b", text.lower())
    digits = []
    for w in words:
        if w.isdigit():
            digits.append(w)
        elif w in WORD_TO_DIGIT:
            digits.append(WORD_TO_DIGIT[w])
    
    combined_digits = "".join(digits)
    if len(combined_digits) >= 4:
        return combined_digits[:8]
    
    return None

def set_pending_power_action(session_id: str, action: str, delay_seconds: int = 5):
    """Sets a pending power action waiting for PIN confirmation."""
    _PENDING_POWER_ACTIONS[session_id] = {
        "action": action.lower().strip(),
        "delay_seconds": delay_seconds,
        "timestamp": time.time()
    }

def get_pending_power_action(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves active pending power action if within expiration window."""
    if session_id in _PENDING_POWER_ACTIONS:
        entry = _PENDING_POWER_ACTIONS[session_id]
        if time.time() - entry["timestamp"] <= AUTH_TIMEOUT_SECONDS:
            return entry
        else:
            del _PENDING_POWER_ACTIONS[session_id]
    return None

def clear_pending_power_action(session_id: str):
    """Clears any pending power action for the given session."""
    if session_id in _PENDING_POWER_ACTIONS:
        del _PENDING_POWER_ACTIONS[session_id]
