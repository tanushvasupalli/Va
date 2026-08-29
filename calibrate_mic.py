import time
import sys
import numpy as np
import sounddevice as sd
from core.audio_io import audio_io
import config

def calibrate():
    print("==================================================")
    print("        MICROPHONE REAL-TIME CALIBRATION TOOL      ")
    print("==================================================")
    print(" 1. Speak into your microphone normally (say 'Wednesday').")
    print(" 2. Watch the live volume bar below.")
    print(" 3. Press Ctrl+C when finished.")
    print("==================================================")

    # List input devices
    devices = sd.query_devices()
    default_in = sd.default.device[0]
    print(f"\n[Active Input Device]: {devices[default_in]['name']}")
    print(f"[Current Threshold]: {config.VAD_ENERGY_THRESHOLD:.4f}")
    print(f"[Current Mic Gain]: {config.MIC_GAIN}x\n")

    audio_io.start_stream()

    try:
        while True:
            chunk = audio_io.read_chunk(timeout=0.1)
            rms = audio_io.calculate_rms(chunk)
            
            # Create a 30-block ASCII visual meter
            bars = int(min(rms * 1500, 30))
            meter = "█" * bars + "░" * (30 - bars)
            
            status = " [SPEAKING DETECTED!]" if rms > config.VAD_ENERGY_THRESHOLD else ""
            sys.stdout.write(f"\rVolume: [{meter}] RMS: {rms:.4f}{status}    ")
            sys.stdout.flush()
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n[Calibration stopped]")
        audio_io.stop_stream()

if __name__ == "__main__":
    calibrate()
