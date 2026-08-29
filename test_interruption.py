import sys
import time
import threading
import numpy as np

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.speaker import speaker
from core.interruption import speak_with_barge_in
from core.wake_word import wake_word_detector
from core.brain import brain

def test_interruption_logic():
    print("==================================================")
    print("       VOICE BARGE-IN & INTERRUPTION TEST         ")
    print("==================================================")

    # 1. Test immediate cutoff using speaker.stop()
    print("\n--- [1/3] Testing Immediate Speaker Stop ---")
    long_text = "This is a very long speech test to ensure that when Wednesday is speaking, any call to stop immediately cuts off audio without hanging or playing to the end of the sentence."
    
    cutoff_time = [None]
    def _delayed_stop():
        # Wait until speaker is actually active
        while not speaker.is_speaking:
            time.sleep(0.05)
        print(">> [Playback Active]: Triggering interrupt / speaker.stop() now...")
        t0 = time.time()
        speaker.stop()
        cutoff_time[0] = time.time() - t0

    threading.Thread(target=_delayed_stop, daemon=True).start()
    interrupted = speaker.speak(long_text)
    print(f">> Speaker interrupted status: {interrupted}")
    print(f">> Audio cut off latency: {cutoff_time[0]:.3f}s")
    assert interrupted is True, "Speaker did not report interrupted status!"

    # 2. Test Wake Word Interruption Parsing
    print("\n--- [2/3] Testing Wake Word Barge-In Extraction ---")
    simulated_utterance = "Wednesday what time is it"
    triggered, command = wake_word_detector.is_wake_word_present(simulated_utterance)
    print(f"Simulated Utterance: '{simulated_utterance}'")
    print(f"Barge-in Triggered: {triggered} | Extracted New Command: '{command}'")
    assert triggered is True
    assert "time" in command

    # 3. Test Full Interrupted Task Execution
    print("\n--- [3/3] Testing Switching & Executing New Interrupted Task ---")
    print(f"Sending extracted command ('{command}') to Wednesday's Brain...")
    new_response = brain.query(command, source="voice", speaker="Tanush", is_owner=True)
    print(f"[Wednesday's New Response]: {new_response}")
    print("Speaking new response out loud...")
    speaker.speak(new_response)

    print("\n==================================================")
    print("     ALL INTERRUPTION TESTS PASSED CLEANLY!       ")
    print("==================================================")

if __name__ == "__main__":
    test_interruption_logic()
