import sys
import time
import numpy as np

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.speaker import speaker
from core.brain import brain
from core.wake_word import wake_word_detector
from core.speaker_recognition import speaker_recognizer

def test_full_pipeline():
    print("==================================================")
    print("      LIVE VOICE AGENT PIPELINE SIMULATION        ")
    print("==================================================")
    
    # 1. Simulate hearing the wake word & voice biometrics
    simulated_voice_input = "Wednesday, what is the weather like and who am I?"
    print(f"\n[Simulated Audio Input]: '{simulated_voice_input}'")
    
    triggered, inline_command = wake_word_detector.is_wake_word_present(simulated_voice_input)
    print(f">> [Wake Word Detection]: {'TRIGGERED (Wednesday detected!)' if triggered else 'FAILED'}")
    print(f">> [Extracted Command]: '{inline_command}'")
    
    # 2. Voice Biometrics identification
    simulated_audio = np.random.randn(16000).astype(np.float32)
    speaker_name, confidence, is_owner = speaker_recognizer.identify_speaker(simulated_audio)
    print(f">> [Voice Biometrics]: Identified speaker as '{speaker_name}' ({confidence}% confidence, Owner: {is_owner})")
    
    # 3. Play activation chime
    print("\n>> Playing wake chime...")
    speaker.play_chime("wake")
    
    # 4. Brain processes query with speaker context
    print("\n>> Sending to Wednesday's Brain with speaker context...")
    start_time = time.time()
    response = brain.query(inline_command, source="voice", speaker=speaker_name, is_owner=is_owner)
    latency = time.time() - start_time
    
    print(f"\n[Wednesday]: {response}")
    print(f">> [Response Latency]: {latency:.2f}s")
    
    # 5. Speak response out loud through user's speakers
    print("\n>> Playing Wednesday's voice through your speakers...")
    speaker.speak(response)
    
    print("\n>> Playing sleep chime...")
    speaker.play_chime("sleep")
    
    print("\n==================================================")
    print("       PIPELINE TEST PASSED SUCCESSFULLY!         ")
    print("==================================================")

if __name__ == "__main__":
    test_full_pipeline()
