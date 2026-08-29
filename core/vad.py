import time
import numpy as np
from core.audio_io import audio_io
import config

class VADDetector:
    """Voice Activity Detector that segments user speech and detects silence endpoints."""

    def __init__(
        self,
        energy_threshold: float = config.VAD_ENERGY_THRESHOLD,
        silence_limit: float = config.VAD_SILENCE_LIMIT,
        max_duration: float = config.MAX_RECORDING_SECONDS
    ):
        self.energy_threshold = energy_threshold
        self.silence_limit = silence_limit
        self.max_duration = max_duration

    def record_until_silence(self, timeout_initial_speech: float = 6.0) -> list[np.ndarray]:
        """
        Records user speech until a pause/silence is detected.
        """
        recorded_frames: list[np.ndarray] = []
        is_speech_started = False
        silence_start_time = None
        start_time = time.time()

        # Rolling pre-buffer (last ~400ms) to ensure the very first sound isn't clipped
        pre_buffer = []
        pre_buffer_max_chunks = int((config.SAMPLE_RATE * 0.4) / config.CHUNK_SIZE)

        while True:
            chunk = audio_io.read_chunk(timeout=0.1)
            energy = audio_io.calculate_rms(chunk)
            current_time = time.time()

            if not is_speech_started:
                pre_buffer.append(chunk)
                if len(pre_buffer) > pre_buffer_max_chunks:
                    pre_buffer.pop(0)

                if energy > self.energy_threshold:
                    is_speech_started = True
                    recorded_frames.extend(pre_buffer)
                    recorded_frames.append(chunk)
                    silence_start_time = None
                elif timeout_initial_speech > 0 and (current_time - start_time) > timeout_initial_speech:
                    return []
            else:
                recorded_frames.append(chunk)

                if energy > self.energy_threshold:
                    silence_start_time = None
                else:
                    if silence_start_time is None:
                        silence_start_time = current_time
                    elif current_time - silence_start_time >= self.silence_limit:
                        break

                if (current_time - start_time) >= self.max_duration:
                    break

        return recorded_frames

# Global singleton instance
vad_detector = VADDetector()
