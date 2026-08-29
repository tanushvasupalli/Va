import sys
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.audio_io import audio_io
from core.vad import vad_detector
from core.transcriber import transcriber
from core.wake_word import wake_word_detector
from core.speaker_recognition import speaker_recognizer
from core.brain import brain
from core.speaker import speaker
from core.interruption import speak_with_barge_in
import config

def print_banner():
    enrolled = speaker_recognizer.list_enrolled_speakers()
    enrolled_str = ", ".join(f"{s['name']} (Owner)" if s['is_owner'] else s['name'] for s in enrolled) if enrolled else "None (Run 'python enroll_voice.py' to register)"
    print(f"""
============================================================
              WEDNESDAY - AI VOICE AGENT                   
============================================================
 [Status] System Initialized & Running
 [Wake Word] Say "Wednesday" to activate or interrupt
 [Barge-In] Interrupt anytime by saying "Wednesday"
 [Voice Profiles] {enrolled_str}
 [Exit] Press Ctrl+C in terminal to stop
============================================================
""")

def execute_command_cycle(user_command: str, active_frames: list) -> tuple[bool, str, list]:
    """
    Executes a single user command cycle with voice biometrics, brain reasoning,
    and interruptible voice response with barge-in support.
    
    Returns:
        tuple[bool, str, list]: (has_interrupted_command, next_command, next_frames)
    """
    # 1. Voice Biometrics & Speaker Identification
    speaker_name, confidence, is_owner = speaker_recognizer.identify_speaker(active_frames)
    status_tag = "Verified Owner" if is_owner else "Guest Voice"
    print(f"[Voice Biometrics]: Speaker identified as '{speaker_name}' ({confidence}% match | {status_tag})")
    print(f"[You ({speaker_name})]: {user_command}")

    # 2. Check for quick exit commands
    if user_command.lower().strip() in ["stop", "never mind", "cancel", "go to sleep", "sleep"]:
        speaker.speak("Going to standby.")
        speaker.play_chime("sleep")
        return False, "", []

    # 3. Process in Brain with Speaker Context
    print("[State: THINKING] Wednesday is processing...")
    response = brain.query(user_command, source="voice", speaker=speaker_name, is_owner=is_owner)
    print(f"[Wednesday]: {response}")

    # 4. Speak Response with Barge-In / Interruption Support
    print("[State: SPEAKING] Playing audio (say 'Wednesday' anytime to interrupt)...")
    interrupted, new_cmd, new_frames = speak_with_barge_in(response)

    if interrupted:
        print("\n⚡ [Barge-In Action]: Audio cut off immediately.")
        speaker.play_chime("wake")
        if not new_cmd:
            print("[State: LISTENING] Speak your new request...")
            frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)
            if frames:
                new_cmd = transcriber.transcribe(frames)
                new_frames = frames

        if new_cmd and new_cmd.strip():
            return True, new_cmd, new_frames
        return False, "", []

    # 5. Follow-up Conversation Loop (Stays awake for 6s)
    while True:
        print(f"\n[State: FOLLOW-UP] Listening for follow-up from {speaker_name} (6s)...")
        follow_up_frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)

        if not follow_up_frames:
            print("[State: TIMEOUT] Returning to standby.")
            speaker.play_chime("sleep")
            break

        follow_up_text = transcriber.transcribe(follow_up_frames)
        if not follow_up_text.strip():
            break

        # Check if wake word was explicitly said in follow-up
        triggered, inline_cmd = wake_word_detector.is_wake_word_present(follow_up_text)
        if triggered and inline_cmd:
            follow_up_text = inline_cmd

        if follow_up_text.lower().strip() in ["stop", "never mind", "cancel", "bye", "go to sleep", "sleep"]:
            speaker.speak("Until next time.")
            speaker.play_chime("sleep")
            break

        # Identify speaker in follow-up
        fu_speaker, fu_conf, fu_owner = speaker_recognizer.identify_speaker(follow_up_frames)
        print(f"\n[You ({fu_speaker})]: {follow_up_text}")

        # Brain & Speak with Barge-In
        print("[State: THINKING] Processing follow-up...")
        follow_up_reply = brain.query(follow_up_text, source="voice", speaker=fu_speaker, is_owner=fu_owner)
        print(f"[Wednesday]: {follow_up_reply}")

        fu_interrupted, fu_new_cmd, fu_new_frames = speak_with_barge_in(follow_up_reply)
        if fu_interrupted:
            print("\n⚡ [Barge-In Action]: Audio cut off immediately in follow-up.")
            speaker.play_chime("wake")
            if not fu_new_cmd:
                print("[State: LISTENING] Speak your new request...")
                frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)
                if frames:
                    fu_new_cmd = transcriber.transcribe(frames)
                    fu_new_frames = frames
            if fu_new_cmd and fu_new_cmd.strip():
                return True, fu_new_cmd, fu_new_frames
            break

    return False, "", []

def run_agent():
    print_banner()

    # Start non-blocking microphone stream
    try:
        audio_io.start_stream()
    except Exception as e:
        print(f"[Error] Failed to access default microphone: {e}")
        print("Please check your Windows microphone settings and permissions.")
        sys.exit(1)

    # Initial friendly greeting
    speaker.speak("Wednesday is ready.")

    while True:
        try:
            print("\n[State: IDLE] Listening for 'Wednesday'...")
            
            # 1. Listen for Wake Word
            triggered, inline_command, wake_frames = wake_word_detector.listen_for_wake_word()

            if not triggered:
                time.sleep(0.05)
                continue

            # 2. Wake Word Triggered!
            print("\n>>> [Wake Word Detected!]")
            speaker.play_chime("wake")

            current_command = inline_command
            current_frames = wake_frames

            # 3. If no inline command was said with "Wednesday", record the user's speech
            if not current_command:
                print("[State: LISTENING] Speak your request...")
                frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)
                if not frames:
                    print("[Notice] No speech detected.")
                    speaker.play_chime("sleep")
                    continue

                current_frames = frames
                print("[State: THINKING] Transcribing...")
                current_command = transcriber.transcribe(frames)

            if not current_command.strip():
                print("[Notice] Could not recognize speech.")
                continue

            # 4. Run Command Cycle & Handle Interruption Chains
            while current_command and current_command.strip():
                has_interrupted, next_cmd, next_frames = execute_command_cycle(current_command, current_frames)
                if has_interrupted and next_cmd:
                    current_command = next_cmd
                    current_frames = next_frames
                else:
                    break

        except KeyboardInterrupt:
            print("\n[Shutting down] Goodbye!")
            speaker.stop()
            audio_io.stop_stream()
            break
        except Exception as e:
            print(f"\n[Unexpected Error]: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_agent()
