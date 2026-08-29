import sys
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.audio_io import audio_io
from core.vad import vad_detector
from core.speaker import speaker
from core.speaker_recognition import speaker_recognizer
import config

SAMPLE_PROMPTS = [
    "Wednesday, what is the weather like today?",
    "The quick brown fox jumps over the lazy dog.",
    "Open my browser and tell me the latest news."
]

def print_banner():
    print("""
============================================================
       WEDNESDAY - VOICE RECOGNITION ENROLLMENT            
============================================================
 Calibrate and register your unique voice biometric profile.
 This allows Wednesday to identify you, personalize answers,
 and verify authorized voice commands.
============================================================
""")

def run_enrollment():
    print_banner()

    # Get user name
    try:
        user_name = input("Enter your name (e.g. Tanush) [Default: Tanush]: ").strip()
        if not user_name:
            user_name = "Tanush"
    except (KeyboardInterrupt, EOFError):
        print("\nEnrollment cancelled.")
        return

    print(f"\n[Ready to Enroll]: '{user_name}'")
    print("You will speak 3 short sample phrases to calibrate your voice print.")
    input("Press ENTER when you are ready to start...")

    # Start audio stream
    try:
        audio_io.start_stream()
    except Exception as e:
        print(f"[Error] Could not start microphone stream: {e}")
        return

    audio_samples = []

    for idx, prompt_text in enumerate(SAMPLE_PROMPTS, 1):
        print(f"\n--- [Sample {idx}/3] ---")
        print(f"Please read this aloud clearly:")
        print(f"👉 \"{prompt_text}\"")
        time.sleep(0.5)

        speaker.play_chime("wake")
        print("\n[Listening...] Speak now...")
        audio_io.clear_queue()
        
        frames = vad_detector.record_until_silence(timeout_initial_speech=7.0)

        if not frames:
            print("[Warning] No speech detected for this sample. Retrying...")
            time.sleep(1)
            continue

        print(">> Captured sample successfully!")
        speaker.play_chime("sleep")
        audio_samples.append(frames)
        time.sleep(0.5)

    if len(audio_samples) < 2:
        print("\n[Failed] Not enough clear audio samples recorded. Please try again.")
        audio_io.stop_stream()
        return

    print("\n[Processing] Extracting acoustic voiceprint and calibrating profile...")
    success = speaker_recognizer.enroll_speaker(user_name, audio_samples, is_owner=True)

    if success:
        print(f"\n✨ [SUCCESS] Voice profile for '{user_name}' successfully created and saved!")
        print(f"Profile saved to: {config.BASE_DIR / 'data' / 'profiles' / (user_name.lower() + '.json')}")
        
        # Test verification immediately
        print("\n--- [Instant Verification Test] ---")
        print("Say a quick phrase to test recognition...")
        speaker.play_chime("wake")
        audio_io.clear_queue()
        test_frames = vad_detector.record_until_silence(timeout_initial_speech=5.0)
        
        if test_frames:
            identified_name, confidence, is_owner = speaker_recognizer.identify_speaker(test_frames)
            print(f">> [Identified Speaker]: {identified_name}")
            print(f">> [Confidence Score]: {confidence}%")
            print(f">> [Owner Status]: {'Verified Owner' if is_owner else 'Guest'}")
            speaker.speak(f"Voice recognized. Welcome back, {identified_name}.")
        else:
            speaker.speak(f"Voice profile for {user_name} has been enrolled successfully.")
    else:
        print(f"\n[Error] Could not enroll voice profile. Please ensure microphone is active and retry.")

    audio_io.stop_stream()
    print("\n============================================================")
    print("Enrollment complete! Launch 'python main.py' to run Wednesday.")
    print("============================================================\n")

if __name__ == "__main__":
    run_enrollment()
