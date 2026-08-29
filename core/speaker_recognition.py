import os
import json
import time
import io
from pathlib import Path
from typing import Optional, Tuple, Dict, List
import numpy as np
import soundfile as sf
import config

def _pure_numpy_dct_ii(x: np.ndarray, num_ceps: int = 13) -> np.ndarray:
    """
    Computes Type-II Discrete Cosine Transform (ortho-normalized) using pure numpy.
    Zero external C-extension DLL dependencies (immune to Windows AppLocker/Control policies).
    """
    if x.ndim == 1:
        x = x[None, :]
    num_frames, num_filters = x.shape
    k = np.arange(num_ceps)[:, None]          # shape: (num_ceps, 1)
    n = np.arange(num_filters)[None, :]        # shape: (1, num_filters)
    # Cosine basis matrix: shape (num_ceps, num_filters)
    basis = np.cos(np.pi * k * (2 * n + 1) / (2.0 * num_filters))
    
    # Project: (num_frames, num_filters) @ (num_filters, num_ceps) -> (num_frames, num_ceps)
    transformed = np.dot(x, basis.T) * np.sqrt(2.0 / num_filters)
    transformed[:, 0] *= (1.0 / np.sqrt(2.0))
    return transformed

class SpeakerRecognizer:
    """
    Acoustic Voice Biometrics and Speaker Recognition system.
    Extracts acoustic spectral features, pitch distribution, and MFCCs
    to build voiceprints and identify speakers with zero cloud latency.
    """

    def __init__(self, profiles_dir: Optional[Path] = None):
        self.profiles_dir = profiles_dir or (config.BASE_DIR / "data" / "profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = config.SAMPLE_RATE
        self.profiles: Dict[str, dict] = {}
        self.similarity_threshold = 0.72  # Cosine similarity threshold for verification
        self.load_profiles()

    def load_profiles(self):
        """Loads all saved speaker profiles from disk."""
        self.profiles.clear()
        for filepath in self.profiles_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = data.get("name")
                    if name and "embedding" in data:
                        data["embedding"] = np.array(data["embedding"], dtype=np.float32)
                        self.profiles[name.lower()] = data
            except Exception as e:
                print(f"[SpeakerRecognizer Notice] Error loading profile {filepath.name}: {e}")

    def save_profile(self, name: str, embedding: np.ndarray, is_owner: bool = True, metadata: dict = None) -> bool:
        """Saves a speaker profile embedding to disk."""
        try:
            profile_data = {
                "name": name.strip(),
                "is_owner": is_owner,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "embedding": embedding.tolist(),
                "metadata": metadata or {}
            }
            safe_filename = "".join(c for c in name if c.isalnum() or c in ("-", "_")).lower() or "speaker"
            filepath = self.profiles_dir / f"{safe_filename}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)
            self.load_profiles()
            return True
        except Exception as e:
            print(f"[SpeakerRecognizer Error] Failed to save profile for {name}: {e}")
            return False

    def list_enrolled_speakers(self) -> List[dict]:
        """Returns metadata for all enrolled speakers."""
        result = []
        for name, data in self.profiles.items():
            result.append({
                "name": data.get("name", name),
                "is_owner": data.get("is_owner", False),
                "created_at": data.get("created_at", "")
            })
        return result

    def delete_profile(self, name: str) -> bool:
        """Deletes an enrolled speaker profile."""
        safe_filename = "".join(c for c in name if c.isalnum() or c in ("-", "_")).lower()
        filepath = self.profiles_dir / f"{safe_filename}.json"
        if filepath.exists():
            filepath.unlink()
            self.load_profiles()
            return True
        return False

    def _prepare_audio(self, audio_input) -> np.ndarray:
        """Flattens and normalizes audio frames into a single 1D numpy array."""
        if audio_input is None:
            return np.array([], dtype=np.float32)

        if isinstance(audio_input, list):
            if not audio_input:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(audio_input, axis=0)
        elif isinstance(audio_input, np.ndarray):
            audio = audio_input
        elif isinstance(audio_input, (bytes, bytearray, io.BytesIO)):
            if isinstance(audio_input, (bytes, bytearray)):
                buf = io.BytesIO(audio_input)
            else:
                buf = audio_input
                buf.seek(0)
            audio, _ = sf.read(buf, dtype="float32")
        else:
            return np.array([], dtype=np.float32)

        # Ensure 1D mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        # Normalize amplitude
        max_abs = np.max(np.abs(audio)) if len(audio) > 0 else 0
        if max_abs > 1e-4:
            audio = audio / max_abs

        return audio.astype(np.float32)

    def _extract_mfcc(self, signal: np.ndarray, num_filters: int = 26, num_ceps: int = 13) -> np.ndarray:
        """
        Extracts Mel-Frequency Cepstral Coefficients (MFCC) using FFT, Mel filterbanks, and pure numpy DCT.
        """
        if len(signal) < 512:
            return np.zeros((1, num_ceps), dtype=np.float32)

        # Pre-emphasis filter
        pre_emphasis = 0.97
        emphasized = np.append(signal[0], signal[1:] - pre_emphasis * signal[:-1])

        # Framing
        frame_size = 0.025  # 25ms
        frame_stride = 0.010  # 10ms
        frame_length = int(round(frame_size * self.sample_rate))
        frame_step = int(round(frame_stride * self.sample_rate))
        signal_length = len(emphasized)

        if signal_length <= frame_length:
            pad_signal_length = frame_length
            pad_signal = np.pad(emphasized, (0, pad_signal_length - signal_length), mode="constant")
            num_frames = 1
        else:
            num_frames = int(np.ceil(float(np.abs(signal_length - frame_length)) / frame_step)) + 1
            pad_signal_length = (num_frames - 1) * frame_step + frame_length
            pad_signal = np.pad(emphasized, (0, pad_signal_length - signal_length), mode="constant")

        indices = np.tile(np.arange(0, frame_length), (num_frames, 1)) + \
                  np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
        frames = pad_signal[indices.astype(np.int32, copy=False)]

        # Windowing (Hamming)
        frames *= np.hamming(frame_length)

        # Fourier Transform & Power Spectrum
        nfft = 512
        mag_frames = np.absolute(np.fft.rfft(frames, nfft))
        pow_frames = ((1.0 / nfft) * ((mag_frames) ** 2))

        # Filterbanks
        low_freq_mel = 0
        high_freq_mel = (2595 * np.log10(1 + (self.sample_rate / 2) / 700))
        mel_points = np.linspace(low_freq_mel, high_freq_mel, num_filters + 2)
        hz_points = (700 * (10**(mel_points / 2595) - 1))
        bin = np.floor((nfft + 1) * hz_points / self.sample_rate)

        fbank = np.zeros((num_filters, int(np.floor(nfft / 2 + 1))))
        for m in range(1, num_filters + 1):
            f_m_minus = int(bin[m - 1])
            f_m = int(bin[m])
            f_m_plus = int(bin[m + 1])

            for k in range(f_m_minus, f_m):
                if f_m != f_m_minus:
                    fbank[m - 1, k] = (k - bin[m - 1]) / (bin[m] - bin[m - 1])
            for k in range(f_m, f_m_plus):
                if f_m_plus != f_m:
                    fbank[m - 1, k] = (bin[m + 1] - k) / (bin[m + 1] - bin[m])

        filter_banks = np.dot(pow_frames, fbank.T)
        filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
        filter_banks = 20 * np.log10(filter_banks)

        # Pure numpy DCT
        mfcc = _pure_numpy_dct_ii(filter_banks, num_ceps=num_ceps)
        return mfcc

    def extract_voiceprint(self, audio_input) -> Optional[np.ndarray]:
        """
        Extracts a compact acoustic voiceprint embedding vector (~46 dimensions)
        capturing pitch, spectral distribution, harmonics, and MFCC statistics.
        """
        signal = self._prepare_audio(audio_input)
        if len(signal) < self.sample_rate * 0.35:  # Require at least 350ms of audio
            return None

        # 1. MFCC stats (Mean and Std across frames = 26 features)
        mfcc = self._extract_mfcc(signal, num_filters=26, num_ceps=13)
        mfcc_mean = np.mean(mfcc, axis=0)
        mfcc_std = np.std(mfcc, axis=0)
        mfcc_skew = np.mean(((mfcc - mfcc_mean) / (mfcc_std + 1e-6)) ** 3, axis=0)

        # 2. Spectral Centroid & Rolloff
        nfft = 512
        frame_len = int(0.025 * self.sample_rate)
        hop_len = int(0.010 * self.sample_rate)
        num_frames = max(1, (len(signal) - frame_len) // hop_len)
        
        centroids = []
        rolloffs = []
        zcrs = []

        for i in range(num_frames):
            frame = signal[i * hop_len : i * hop_len + frame_len]
            if len(frame) < frame_len:
                break
            
            # Zero crossing rate
            zcr = np.mean(np.abs(np.diff(np.signbit(frame).astype(int))))
            zcrs.append(zcr)

            # Spectrum
            spectrum = np.abs(np.fft.rfft(frame * np.hamming(len(frame)), nfft))
            freqs = np.fft.rfftfreq(nfft, 1.0 / self.sample_rate)

            # Centroid
            sum_spec = np.sum(spectrum)
            if sum_spec > 1e-6:
                centroid = np.sum(freqs * spectrum) / sum_spec
                centroids.append(centroid)

                # Rolloff (85% energy)
                cum_energy = np.cumsum(spectrum)
                threshold = 0.85 * cum_energy[-1]
                idx = np.where(cum_energy >= threshold)[0]
                rolloff = freqs[idx[0]] if len(idx) > 0 else 0
                rolloffs.append(rolloff)

        c_mean = np.mean(centroids) if centroids else 0.0
        c_std = np.std(centroids) if centroids else 0.0
        r_mean = np.mean(rolloffs) if rolloffs else 0.0
        r_std = np.std(rolloffs) if rolloffs else 0.0
        z_mean = np.mean(zcrs) if zcrs else 0.0
        z_std = np.std(zcrs) if zcrs else 0.0

        # 3. Fundamental frequency (Pitch estimation via autocorrelation)
        corr = np.correlate(signal[:min(len(signal), self.sample_rate)], signal[:min(len(signal), self.sample_rate)], mode='full')
        corr = corr[len(corr)//2:]
        # Human pitch range ~ 70Hz to 350Hz -> lag between sr/350 and sr/70
        d_min = int(self.sample_rate / 350)
        d_max = int(self.sample_rate / 70)
        if len(corr) > d_max:
            peak = np.argmax(corr[d_min:d_max]) + d_min
            f0_estimate = self.sample_rate / peak if peak > 0 else 0.0
        else:
            f0_estimate = 0.0

        # Assemble full feature vector (13 + 13 + 13 + 2 + 2 + 2 + 1 = 46 dimensions)
        feature_vector = np.concatenate([
            mfcc_mean,
            mfcc_std,
            mfcc_skew,
            [c_mean / 4000.0, c_std / 2000.0],
            [r_mean / 6000.0, r_std / 3000.0],
            [z_mean * 5.0, z_std * 5.0],
            [f0_estimate / 300.0]
        ])

        # L2-normalize vector for cosine similarity
        norm = np.linalg.norm(feature_vector)
        if norm > 1e-6:
            feature_vector = feature_vector / norm

        return feature_vector.astype(np.float32)

    def enroll_speaker(self, name: str, audio_samples: list, is_owner: bool = True) -> bool:
        """
        Enrolls a speaker by aggregating voiceprints from multiple sample recordings.
        """
        embeddings = []
        for sample in audio_samples:
            emb = self.extract_voiceprint(sample)
            if emb is not None:
                embeddings.append(emb)

        if not embeddings:
            print(f"[SpeakerRecognizer Warning] No valid voiceprints could be extracted for {name}.")
            return False

        # Average and re-normalize embeddings
        avg_emb = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg_emb)
        if norm > 1e-6:
            avg_emb = avg_emb / norm

        return self.save_profile(name, avg_emb, is_owner=is_owner, metadata={"num_samples": len(embeddings)})

    def identify_speaker(self, audio_input) -> Tuple[str, float, bool]:
        """
        Identifies the speaker from an audio sample.
        
        Returns:
            Tuple[speaker_name, confidence_pct, is_owner]:
            - speaker_name: e.g. "Tanush", "Guest", "Unenrolled"
            - confidence_pct: float 0.0 to 100.0
            - is_owner: True if identified speaker is the registered owner
        """
        if not self.profiles:
            # If no speaker profiles are enrolled yet, default to generic owner
            return "Owner (Unenrolled)", 100.0, True

        query_emb = self.extract_voiceprint(audio_input)
        if query_emb is None:
            return "Unknown", 0.0, False

        best_speaker = "Guest"
        best_score = -1.0
        best_is_owner = False

        for name, profile in self.profiles.items():
            ref_emb = profile["embedding"]
            # Cosine similarity
            similarity = float(np.dot(query_emb, ref_emb))
            if similarity > best_score:
                best_score = similarity
                best_speaker = profile.get("name", name)
                best_is_owner = profile.get("is_owner", False)

        # Normalize score to percentage
        confidence_pct = max(0.0, min(100.0, ((best_score + 1.0) / 2.0) * 100.0))

        if best_score >= self.similarity_threshold:
            return best_speaker, round(confidence_pct, 1), best_is_owner
        else:
            return "Guest", round(confidence_pct, 1), False

    def is_owner_speaking(self, audio_input) -> bool:
        """Quick check whether the audio belongs to the enrolled owner."""
        _, _, is_owner = self.identify_speaker(audio_input)
        return is_owner

# Global singleton instance
speaker_recognizer = SpeakerRecognizer()
