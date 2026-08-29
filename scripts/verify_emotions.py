import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.speaker import analyze_emotional_context, ENGLISH_VOICE

samples = [
    ("English Witty", "Fascinating. I suppose I can help you with that, darling."),
    ("English Cheerful", "Congratulations! That is amazing and wonderful news!"),
    ("English Empathetic", "I am so sorry to hear that. Please take care, worry not."),
    ("English Serious", "Warning: Critical battery level detected."),
    ("English Calm", "The current time is 10:30 PM.")
]

for label, text in samples:
    emotion, rate, pitch = analyze_emotional_context(text)
    print(f"[{label}] -> Voice: {ENGLISH_VOICE} | Emotion: {emotion} (Rate: {rate}, Pitch: {pitch})")
