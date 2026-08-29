import time
import threading
import numpy as np
from typing import Tuple, List, Optional

from core.audio_io import audio_io
from core.vad import vad_detector
from core.transcriber import transcriber
from core.wake_word import wake_word_detector
from core.speaker import speaker
import config

class InterruptionMonitor:
    """
    Monitors audio input for the 'Wednesday' wake word while the assistant
    is speaking or executing tasks, allowing real-time voice barge-in.
    """

    def __init__(self):
        self.is_monitoring = False

    def listen_during_speaking(self, stop_event: threading.Event) -> Tuple[bool, str, List[np.ndarray]]:
        """
        Continuously listens to microphone chunks while audio is playing.
        If user speaks 'Wednesday', instantly sets stop_event, halts playback,
        and returns the newly detected command.
        
        Returns:
            Tuple[is_interrupted, extracted_command, audio_frames]
        """
        recorded_frames: List[np.ndarray] = []
        is_speech_started = False
        silence_start_time = None
        pre_buffer = []
        pre_buffer_chunks = int((config.SAMPLE_RATE * 0.3) / config.CHUNK_SIZE)

        while not stop_event.is_set():
            chunk = audio_io.read_chunk(timeout=0.08)
            energy = audio_io.calculate_rms(chunk)
            current_time = time.time()

            if not is_speech_started:
                pre_buffer.append(chunk)
                if len(pre_buffer) > pre_buffer_chunks:
                    pre_buffer.pop(0)

                # Slightly higher threshold during playback to avoid triggering on faint speaker bleed
                threshold = config.VAD_ENERGY_THRESHOLD * 1.3
                if energy > threshold:
                    is_speech_started = True
                    recorded_frames.extend(pre_buffer)
                    recorded_frames.append(chunk)
                    silence_start_time = None
            else:
                recorded_frames.append(chunk)
                threshold = config.VAD_ENERGY_THRESHOLD * 1.3

                if energy > threshold:
                    silence_start_time = None
                else:
                    if silence_start_time is None:
                        silence_start_time = current_time
                    elif current_time - silence_start_time >= 0.35:
                        # End of utterance reached, evaluate for wake word
                        break

                # Max continuous speech segment
                if len(recorded_frames) * (config.CHUNK_SIZE / config.SAMPLE_RATE) >= 8.0:
                    break

        if not recorded_frames:
            return False, "", []

        # Transcribe the utterance captured while speaking
        transcript = transcriber.transcribe(recorded_frames)
        if not transcript:
            return False, "", []

        triggered, command = wake_word_detector.is_wake_word_present(transcript)
        if triggered:
            # STOP ALL PLAYBACK IMMEDIATELY
            stop_event.set()
            speaker.stop()
            print(f"\n⚡ [Interruption Detected]: Heard \"{transcript}\" -> Command: \"{command or '(Awaiting task)'}\"")
            return True, command, recorded_frames

        return False, "", []

def speak_with_barge_in(text: str, voice: Optional[str] = None) -> Tuple[bool, str, List[np.ndarray]]:
    """
    Speaks the given text out loud while actively listening for user interruptions.
    
    If the user says 'Wednesday', speech is instantly cut off and the newly
    spoken command/audio is returned.
    
    Returns:
        Tuple[was_interrupted, new_command, new_audio_frames]
    """
    if getattr(config, "MUTE_AGENT_VOICE", False):
        return False, "", []

    stop_event = threading.Event()
    interrupt_result = [False, "", []]

    monitor = InterruptionMonitor()

    def _speak_worker():
        speaker.speak(text, voice=voice, stop_event=stop_event)
        # When playback completes naturally, signal the listener loop to exit
        if not stop_event.is_set():
            stop_event.set()

    def _listen_worker():
        was_interrupted, cmd, frames = monitor.listen_during_speaking(stop_event)
        if was_interrupted:
            interrupt_result[0] = True
            interrupt_result[1] = cmd
            interrupt_result[2] = frames

    speak_thread = threading.Thread(target=_speak_worker, daemon=True)
    listen_thread = threading.Thread(target=_listen_worker, daemon=True)

    speak_thread.start()
    listen_thread.start()

    speak_thread.join()
    listen_thread.join(timeout=0.5)

    return interrupt_result[0], interrupt_result[1], interrupt_result[2]

interruption_monitor = InterruptionMonitor()
