import io
import speech_recognition as sr
from typing import Optional, Tuple
from groq import Groq
from core.audio_io import audio_io
import config

class Transcriber:
    """
    Multi-Engine Speech-to-Text Recognition module.
    - Primary Engine: Groq Whisper (whisper-large-v3-turbo, ~200ms latency)
    - Fallback Engine: SpeechRecognition (Google STT & local recognizer)
    """

    def __init__(self, api_key: str = config.GROQ_API_KEY):
        self.api_key = api_key
        self.client = None
        self.sr_recognizer = sr.Recognizer()
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"[Transcriber Error] Failed to initialize Groq client: {e}")

    def update_key(self, api_key: str):
        """Updates the API key dynamically."""
        self.api_key = api_key
        try:
            self.client = Groq(api_key=self.api_key)
        except Exception as e:
            print(f"[Transcriber Error] Groq client update failed: {e}")

    def _transcribe_groq(self, wav_bytes: bytes, language: str = "en") -> Optional[str]:
        """Transcribes audio using Groq Whisper."""
        if not self.client:
            if config.GROQ_API_KEY:
                self.update_key(config.GROQ_API_KEY)
            else:
                return None

        if not self.client:
            return None

        try:
            kwargs = {
                "file": ("audio.wav", wav_bytes),
                "model": "whisper-large-v3-turbo",
                "response_format": "text",
                "temperature": 0.0,
                "language": language or "en"
            }
            transcription = self.client.audio.transcriptions.create(**kwargs)
            return str(transcription).strip()
        except Exception as e:
            print(f"[Transcriber Notice] Groq Whisper STT unavailable ({e}), trying fallback...")
            return None

    def _transcribe_fallback(self, wav_buffer: io.BytesIO, language: str = "en-US") -> str:
        """Fallback transcription using SpeechRecognition (Google STT)."""
        try:
            wav_buffer.seek(0)
            with sr.AudioFile(wav_buffer) as source:
                audio_data = self.sr_recognizer.record(source)
                text = self.sr_recognizer.recognize_google(audio_data, language=language)
                return text.strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[Transcriber Error] Fallback STT Request failed: {e}")
            return ""
        except Exception as e:
            print(f"[Transcriber Error] Fallback STT failed: {e}")
            return ""

    def transcribe(self, audio_frames: list, language: Optional[str] = "en") -> str:
        """
        Transcribes recorded audio frames into English text with automatic engine fallback.
        
        Args:
            audio_frames: List of recorded numpy audio chunks.
            language: Language code (defaults to 'en').
            
        Returns:
            str: Transcribed text.
        """
        if not audio_frames:
            return ""

        try:
            # Convert audio numpy chunks to WAV in-memory buffer
            wav_buffer: io.BytesIO = audio_io.export_wav_bytes(audio_frames)
            wav_bytes = wav_buffer.read()

            # 1. Try Groq Whisper (Fastest)
            text = self._transcribe_groq(wav_bytes, language=language or "en")
            if text:
                return text

            # 2. Fallback to Google SpeechRecognition
            wav_buffer.seek(0)
            fallback_text = self._transcribe_fallback(wav_buffer, language="en-US")
            if fallback_text:
                print(f"[Transcriber Fallback]: Recognized '{fallback_text}' via Google STT engine.")
                return fallback_text

            return ""
        except Exception as e:
            print(f"[Transcriber Error] STT pipeline failed: {e}")
            return ""

# Global singleton instance
transcriber = Transcriber()
