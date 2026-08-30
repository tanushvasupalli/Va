import os
import sys
import time
import threading
import uvicorn

import config
from core.system_optimizer import optimize_process, cleanup_memory

optimize_process()

def run_dashboard_server():
    """Runs the FastAPI Dashboard on port 8000."""
    try:
        from dashboard.app import app
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    except Exception as e:
        print(f"[Dashboard Error]: {e}")

def run_telegram_service():
    """Runs the Telegram Bot polling loop."""
    try:
        from core.telegram_bot import run_telegram_bot
        run_telegram_bot()
    except Exception as e:
        print(f"[Telegram Notice] Bot stopped: {e}")

def run_voice_loop():
    """Runs local microphone wake-word engine if physical audio devices exist."""
    try:
        from core.audio_io import audio_io
        from core.wake_word import wake_word_detector
        from core.vad import vad_detector
        from core.transcriber import transcriber
        from core.speaker import speaker
        from main import execute_command_cycle

        # Test if microphone stream can start
        audio_io.start_stream()
        if audio_io.stream is None:
            print("[Voice Engine] Headless / mobile environment detected (No local mic stream). Running in Telegram & API mode.")
            return

        print("[Voice Engine] Local microphone active. Listening for 'Wednesday'...")
        while True:
            try:
                triggered, inline_cmd, wake_frames = wake_word_detector.listen_for_wake_word()
                if not triggered:
                    time.sleep(0.05)
                    continue

                speaker.play_chime("wake")
                current_cmd = inline_cmd
                current_frames = wake_frames

                if not current_cmd:
                    frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)
                    if frames:
                        current_cmd = transcriber.transcribe(frames)
                        current_frames = frames

                if current_cmd and current_cmd.strip():
                    while current_cmd and current_cmd.strip():
                        has_interrupted, next_cmd, next_frames = execute_command_cycle(current_cmd, current_frames)
                        if has_interrupted and next_cmd:
                            current_cmd = next_cmd
                            current_frames = next_frames
                        else:
                            break
            except Exception as e:
                time.sleep(1)
    except Exception as e:
        print(f"[Voice Engine Notice]: Running in headless mode ({e}).")

def main():
    print("""
============================================================
           WEDNESDAY AI ASSISTANT - MASTER RUNNER           
============================================================
 [Mode] Cross-Platform (Phone / Termux / PC)
 [Telegram Bot] Starting...
 [Web Dashboard] http://localhost:8000
 [Voice Engine] Checking audio hardware...
============================================================
""")

    threads = []

    # 1. Telegram Bot Thread
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_BOT_TOKEN != "your_telegram_bot_token_here":
        tg_thread = threading.Thread(target=run_telegram_service, daemon=True, name="TelegramBot")
        tg_thread.start()
        threads.append(tg_thread)
    else:
        print("[Notice] Set TELEGRAM_BOT_TOKEN in .env to enable Telegram conversation & remote control.")

    # 2. Local Voice Engine Thread
    voice_thread = threading.Thread(target=run_voice_loop, daemon=True, name="VoiceEngine")
    voice_thread.start()
    threads.append(voice_thread)

    # 3. Web Dashboard (Main blocking thread)
    run_dashboard_server()

if __name__ == "__main__":
    main()
