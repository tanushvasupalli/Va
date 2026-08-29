import io
import queue
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import config

def find_best_input_device() -> int | None:
    """
    Finds the best active physical microphone on the system,
    filtering out inactive virtual audio devices (e.g. Iriun Webcam, OBS, Virtual Audio).
    """
    try:
        devices = sd.query_devices()
        default_in = sd.default.device[0] if sd.default.device else None
        
        # Check if default device is a virtual webcam or inactive driver
        candidates = []
        for idx, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                name_lower = dev["name"].lower()
                # Prioritize Realtek, Built-in, Array, USB, Headset
                priority = 0
                if "realtek" in name_lower or "array" in name_lower or "microphone array" in name_lower:
                    priority += 10
                if "usb" in name_lower or "headset" in name_lower or "headphone" in name_lower:
                    priority += 8
                if "iriun" in name_lower or "obs" in name_lower or "camo" in name_lower or "virtual" in name_lower:
                    priority -= 15  # Penalize virtual drivers
                if dev["hostapi"] == 0:  # MME standard
                    priority += 2

                candidates.append((priority, idx, dev["name"]))

        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates:
            best_priority, best_idx, best_name = candidates[0]
            print(f"[AudioIO] Auto-selected best input device [{best_idx}]: '{best_name}'")
            return best_idx
        return default_in
    except Exception as e:
        print(f"[AudioIO Notice] Device query: {e}")
        return None

class AudioIO:
    """Handles microphone input stream, device selection, gain, and audio buffering."""

    def __init__(
        self,
        sample_rate: int = config.SAMPLE_RATE,
        channels: int = config.CHANNELS,
        chunk_size: int = config.CHUNK_SIZE,
        gain: float = getattr(config, "MIC_GAIN", 1.8)
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.gain = gain
        self.audio_queue = queue.Queue()
        self.stream = None
        self.device_index = find_best_input_device()

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback invoked by sounddevice for each new audio chunk from the mic."""
        boosted = np.clip(indata * self.gain, -1.0, 1.0)
        self.audio_queue.put(boosted)

    def start_stream(self):
        """Starts continuous non-blocking microphone stream on the selected physical device."""
        if self.stream is None:
            if self.device_index is None:
                self.device_index = find_best_input_device()
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=self.chunk_size,
                device=self.device_index,
                callback=self._audio_callback
            )
            self.stream.start()

    def stop_stream(self):
        """Stops the microphone stream."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def clear_queue(self):
        """Clears any residual audio frames in the queue."""
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

    def read_chunk(self, timeout: float = 0.5) -> np.ndarray:
        """Reads a single chunk from the audio queue."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return np.zeros((self.chunk_size, self.channels), dtype="float32")

    @staticmethod
    def calculate_rms(audio_chunk: np.ndarray) -> float:
        """Calculates the Root Mean Square (energy/volume) of an audio chunk."""
        if len(audio_chunk) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_chunk ** 2)))

    def export_wav_bytes(self, audio_frames: list[np.ndarray]) -> io.BytesIO:
        """Converts a list of recorded numpy chunks into a WAV in-memory byte stream."""
        if not audio_frames:
            full_audio = np.zeros((self.chunk_size, self.channels), dtype="float32")
        else:
            full_audio = np.concatenate(audio_frames, axis=0)

        max_val = np.max(np.abs(full_audio))
        if max_val > 0.01:
            full_audio = full_audio / max_val * 0.95

        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, full_audio, self.sample_rate, format="WAV", subtype="PCM_16")
        wav_buffer.seek(0)
        return wav_buffer

# Global singleton instance
audio_io = AudioIO()
