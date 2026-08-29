import re
from difflib import SequenceMatcher
from core.vad import vad_detector
from core.transcriber import transcriber
import config

class WakeWordDetector:
    """Detects the 'Wednesday' wake word from incoming audio stream."""

    def __init__(self, wake_words: list[str] = config.WAKE_WORDS, similarity_threshold: float = config.WAKE_WORD_SIMILARITY_THRESHOLD):
        self.wake_words = [w.lower().strip() for w in wake_words]
        self.similarity_threshold = similarity_threshold

    def is_wake_word_present(self, text: str) -> tuple[bool, str]:
        """
        Checks if any variation of the wake word is present in the transcribed text.
        
        Returns:
            tuple[bool, str]: (is_detected, remaining_command_text)
        """
        clean_text = text.lower().strip()
        # Remove common punctuation except apostrophe
        clean_text = re.sub(r"[^\w\s\']", "", clean_text)
        words = clean_text.split()

        if not words:
            return False, ""

        # 1. Exact or Substring match
        for wake_word in self.wake_words:
            if wake_word in clean_text:
                idx = clean_text.find(wake_word) + len(wake_word)
                command = clean_text[idx:].strip()
                return True, command

        # 2. Fuzzy match on individual words (e.g. "wednesday", "wensday", "wednesdays")
        for i, word in enumerate(words):
            for target in ["wednesday", "wensday", "wendsday"]:
                ratio = SequenceMatcher(None, word, target).ratio()
                if ratio >= self.similarity_threshold:
                    command = " ".join(words[i+1:]).strip()
                    return True, command

            # Check 2-word phrase (e.g. "hey wednesday")
            if i + 1 < len(words):
                two_words = f"{words[i]} {words[i+1]}"
                for wake_word in self.wake_words:
                    ratio2 = SequenceMatcher(None, two_words, wake_word).ratio()
                    if ratio2 >= self.similarity_threshold:
                        command = " ".join(words[i+2:]).strip()
                        return True, command

        return False, ""

    def listen_for_wake_word(self) -> tuple[bool, str, list]:
        """
        Actively listens until speech is detected, transcribes it, and verifies the wake word.
        
        Returns:
            tuple[bool, str, list]: (is_detected, remaining_command_text, audio_frames)
        """
        frames = vad_detector.record_until_silence(timeout_initial_speech=1.2)
        if not frames:
            return False, "", []

        transcript = transcriber.transcribe(frames)
        if not transcript:
            return False, "", []

        print(f"  [Microphone Heard]: \"{transcript}\"")
        triggered, command = self.is_wake_word_present(transcript)
        return triggered, command, frames

# Global singleton instance
wake_word_detector = WakeWordDetector()
