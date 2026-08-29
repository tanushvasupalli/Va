import sys
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import sounddevice as sd
import numpy as np
from core.speaker import speaker
from core.audio_io import audio_io
from core.brain import brain
from core.transcriber import transcriber
from core.speaker_recognition import speaker_recognizer
from tools.system_tools import get_current_time_and_date
from tools.web_tools import get_weather
import config

def test_speaker():
    print("\n--- [1/5] Testing Voice Output (TTS) & Chime ---")
    print("Playing wake chime...")
    speaker.play_chime("wake")
    time.sleep(0.5)
    print(f"Synthesizing voice using '{config.TTS_VOICE}'...")
    speaker.speak("Hello. I am Wednesday. Your audio output is working perfectly.")
    print(">> Voice test complete!")

def test_microphone_and_voice_recognition():
    print("\n--- [2/5] Testing Microphone & Voice Recognition ---")
    print("Recording 3 seconds of audio from your microphone. Please say a sentence (e.g. 'Wednesday')...")
    
    sample_rate = 16000
    duration = 3
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    
    rms = np.sqrt(np.mean(recording ** 2))
    print(f"Recorded 3s. Volume / Energy (RMS): {rms:.4f}")
    if rms > 0.005:
        print(">> Microphone is receiving clear audio input!")
        
        # Test Speaker Recognition
        name, conf, is_owner = speaker_recognizer.identify_speaker(recording)
        print(f">> [Speaker Recognition]: Identified as '{name}' ({conf}% match, Owner: {is_owner})")
        
        # Test Speech-to-Text
        text = transcriber.transcribe([recording])
        if text:
            print(f">> [Speech-to-Text]: Transcribed: \"{text}\"")
        else:
            print(">> [Speech-to-Text]: No speech detected or STT engine returned empty.")
    else:
        print(">> Warning: Recorded volume is very low. Check your Windows microphone volume or mute switch.")

def test_tools():
    print("\n--- [3/5] Testing Built-in Tools ---")
    time_str = get_current_time_and_date()
    print(f"[Time Tool]: {time_str}")
    
    weather_str = get_weather("London")
    print(f"[Weather Tool]: {weather_str}")
    print(">> Tools working cleanly!")

def test_voice_profiles():
    print("\n--- [4/5] Checking Enrolled Voice Profiles ---")
    profiles = speaker_recognizer.list_enrolled_speakers()
    if profiles:
        print(f">> Found {len(profiles)} enrolled voice profile(s):")
        for p in profiles:
            tag = "Primary Owner" if p.get("is_owner") else "Guest"
            print(f"   - {p['name']} ({tag}, Enrolled: {p.get('created_at', 'N/A')})")
    else:
        print(">> No voice profiles registered yet. Run 'python enroll_voice.py' to register your voice print!")

def test_brain():
    print("\n--- [5/5] Testing Brain / LLM Connection ---")
    if not config.GEMINI_API_KEY and not config.GROQ_API_KEY:
        print(">> Note: No API keys configured in .env yet.")
        print(">> Once you add your free GEMINI_API_KEY or GROQ_API_KEY to .env, Wednesday's brain will activate!")
        return

    print("Sending test query to Wednesday...")
    reply = brain.query("Introduce yourself in one witty sentence.", speaker="Tanush", is_owner=True)
    print(f"[Wednesday's Response]: {reply}")
    print(">> Brain connection successful!")

if __name__ == "__main__":
    print("==================================================")
    print("       WEDNESDAY AI AGENT - SYSTEM DIAGNOSTICS     ")
    print("==================================================")
    test_speaker()
    test_microphone_and_voice_recognition()
    test_tools()
    test_voice_profiles()
    test_brain()
    print("\n==================================================")
    print("Diagnostics complete! Run 'python main.py' to launch.")
    print("==================================================")
