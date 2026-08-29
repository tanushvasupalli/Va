import asyncio
import concurrent.futures
import io
import re
import threading
import time
from typing import Optional, Tuple
import sounddevice as sd
import soundfile as sf
import numpy as np
import edge_tts

import config

# STRICT ENGLISH NEURAL VOICE
ENGLISH_VOICE = config.TTS_VOICE

def find_best_output_device() -> Optional[int]:
    """
    Finds the best active physical speaker/headphone device on the system.
    Honors config.OUTPUT_DEVICE_INDEX if set.
    """
    configured_idx = getattr(config, "OUTPUT_DEVICE_INDEX", None)
    if configured_idx is not None:
        return configured_idx

    try:
        devices = sd.query_devices()
        default_out = sd.default.device[1] if sd.default.device else None
        
        # Check candidates
        candidates = []
        for idx, dev in enumerate(devices):
            if dev.get("max_output_channels", 0) > 0:
                name_lower = dev["name"].lower()
                priority = 0
                if "speaker" in name_lower or "headphone" in name_lower or "realtek" in name_lower:
                    priority += 10
                if "fxsound" in name_lower:
                    priority += 8
                if dev.get("hostapi") == 0:  # MME standard
                    priority += 2
                candidates.append((priority, idx, dev["name"]))

        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates and default_out is None:
            return candidates[0][1]
        return default_out
    except Exception as e:
        print(f"[Speaker Notice] Output device discovery: {e}")
        return None

def _run_async(coro):
    """Safely executes an async coroutine even if called inside an active event loop thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()
    else:
        return asyncio.run(coro)

def analyze_emotional_context(text: str) -> Tuple[str, str, str]:
    """
    Analyzes emotional context and sentiment in English
    to modulate pitch and speech rate dynamically.
    
    Returns:
        Tuple[emotion_name, rate_str, pitch_str]
    """
    lower = text.lower()

    # 1. Cheerful / Excited / Joyful
    if any(k in lower for k in [
        "congratulations", "amazing", "wonderful", "awesome", "great news", "yay", "superb", "fantastic", "brilliant"
    ]):
        return ("cheerful", "+7%", "+4Hz")

    # 2. Empathetic / Comforting / Apologetic
    if any(k in lower for k in [
        "sorry", "apologize", "forgive", "take care", "feel better", "sad", "unfortunate", "worry not"
    ]):
        return ("empathetic", "-6%", "-2Hz")

    # 3. Serious / Urgent / Warning / Alert
    if any(k in lower for k in [
        "warning", "alert", "danger", "error", "crucial", "critical", "urgent", "emergency", "failed", "risk"
    ]):
        return ("serious", "+5%", "+2Hz")

    # 4. Playful / Witty / Sarcastic (Wednesday signature persona)
    if any(k in lower for k in [
        "obviously", "fascinating", "naturally", "darling", "ironic", "suppose",
        "amusing", "intriguing", "hardly", "alas", "bizarre", "pity", "curious"
    ]):
        return ("playful", "+2%", "-3Hz")

    # 5. Calm / Neutral (Default natural flow)
    return ("calm", "+0%", "+0Hz")

class Speaker:
    """Handles English Speech Synthesis with Persona-based Emotional Modulation and Interruption."""

    def __init__(self, default_voice: str = config.TTS_VOICE):
        self.default_voice = default_voice
        self.is_speaking = False
        self.muted = getattr(config, "MUTE_AGENT_VOICE", False)
        self.play_chimes = getattr(config, "PLAY_CHIMES", True)
        self.device_index = find_best_output_device()
        self._stop_event = threading.Event()

    def set_muted(self, muted: bool):
        """Dynamically mute or unmute speech output."""
        self.muted = bool(muted)
        config.MUTE_AGENT_VOICE = bool(muted)

    def set_play_chimes(self, enabled: bool):
        """Dynamically enable or disable chime sound effects."""
        self.play_chimes = bool(enabled)
        config.PLAY_CHIMES = bool(enabled)

    def set_device_index(self, device_idx: Optional[int]):
        """Sets the active output sound device index."""
        self.device_index = device_idx

    def stop(self):
        """Instantly cuts off active audio output."""
        self._stop_event.set()
        try:
            sd.stop()
        except Exception:
            pass
        finally:
            self.is_speaking = False

    async def _generate_audio_bytes(self, text: str, voice: Optional[str] = None) -> bytes:
        """Generates speech audio with English neural voice and emotional modulation."""
        selected_voice = voice or self.default_voice
        emotion, rate, pitch = analyze_emotional_context(text)

        communicate = edge_tts.Communicate(
            text=text,
            voice=selected_voice,
            rate=rate,
            pitch=pitch
        )
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        return bytes(audio_data)

    def speak(self, text: str, voice: Optional[str] = None, stop_event: Optional[threading.Event] = None) -> bool:
        """
        Synthesizes text and plays audio out loud.
        Supports instant interruption if stop() is called or stop_event is provided and set.
        
        Returns:
            bool: True if playback was interrupted mid-speech, False otherwise.
        """
        if self.muted:
            return False

        if not text or not text.strip():
            return False

        self._stop_event.clear()
        self.is_speaking = True
        try:
            audio_bytes = _run_async(self._generate_audio_bytes(text, voice=voice))
            if not audio_bytes:
                return False

            if self._stop_event.is_set() or (stop_event is not None and stop_event.is_set()):
                return True

            audio_buffer = io.BytesIO(audio_bytes)
            data, sample_rate = sf.read(audio_buffer, dtype="float32")

            if self._stop_event.is_set() or (stop_event is not None and stop_event.is_set()):
                return True

            # Start playback non-blockingly to allow real-time interruption checks
            try:
                sd.play(data, samplerate=sample_rate, device=self.device_index)
            except Exception:
                # Fallback to default output device
                sd.play(data, samplerate=sample_rate, device=None)

            # Monitor playback until finished or interrupted
            while True:
                if self._stop_event.is_set() or (stop_event is not None and stop_event.is_set()):
                    self.stop()
                    return True
                try:
                    stream = sd.get_stream()
                    if stream is None or not stream.active:
                        break
                except Exception:
                    break
                time.sleep(0.03)

            return False
        except Exception as e:
            print(f"[Speaker Error] Failed to synthesize/play audio: {e}")
            return False
        finally:
            self.is_speaking = False

    def play_chime(self, chime_type: str = "wake", stop_event: Optional[threading.Event] = None) -> bool:
        """Plays a gentle synthesized notification chime (wake or sleep)."""
        if not self.play_chimes:
            return False

        try:
            sample_rate = 44100
            if chime_type == "wake":
                t1 = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                tone1 = 0.2 * np.sin(2 * np.pi * 523.25 * t1)
                tone2 = 0.25 * np.sin(2 * np.pi * 783.99 * t2)
                window1 = np.hanning(len(tone1))
                window2 = np.hanning(len(tone2))
                audio = np.concatenate([tone1 * window1, tone2 * window2])
            else:
                t = np.linspace(0, 0.15, int(sample_rate * 0.15), False)
                audio = 0.15 * np.sin(2 * np.pi * 440.0 * t) * np.hanning(len(t))

            try:
                sd.play(audio.astype(np.float32), samplerate=sample_rate, device=self.device_index)
            except Exception:
                sd.play(audio.astype(np.float32), samplerate=sample_rate, device=None)

            while True:
                if self._stop_event.is_set() or (stop_event is not None and stop_event.is_set()):
                    self.stop()
                    return True
                try:
                    stream = sd.get_stream()
                    if stream is None or not stream.active:
                        break
                except Exception:
                    break
                time.sleep(0.03)

            return False
        except Exception as e:
            print(f"[Chime Error] Could not play chime: {e}")
            return False

# Global singleton instance
speaker = Speaker()
