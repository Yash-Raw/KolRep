import io
import logging
import os
import struct
import subprocess
import tempfile
import uuid
from typing import Any, Optional

import numpy as np
import scipy.fftpack as fft
import soundfile as sf

from app.services.audio_service import FFMPEG_BIN

logger = logging.getLogger("voicerep.watermark")

# 16-bit Barker-inspired synchronization word
SYNC_BITS = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1]
FRAME_SIZE = 1024
DELTA = 0.08  # QIM quantization step size calibrated for >40dB SNR and MP3 resilience
TARGET_SAMPLE_RATE = 24000
BIN_CENTER_HZ = 2500  # Voice formant energy window


def crc16_ccitt(data: bytes) -> int:
    """Computes standard CRC-16-CCITT for tamper detection."""
    crc = 0xFFFF
    for b in data:
        crc = (crc >> 8) | ((crc & 0xFF) << 8)
        crc ^= b
        crc ^= (crc & 0xFF) >> 4
        crc ^= ((crc << 8) << 4) & 0xFFFF
        crc ^= ((crc & 0xFF) << 4) << 1
    return crc & 0xFFFF


class WatermarkService:
    def __init__(self):
        self.frame_size = FRAME_SIZE
        self.delta = DELTA
        self.target_sr = TARGET_SAMPLE_RATE

    def pack_payload(self, version: int, timestamp: int, user_hash: int, gen_hash: int) -> list[int]:
        """
        Packs metadata into a 136-bit sequence:
        16-bit Sync Word + 8-bit Version + 32-bit Timestamp + 32-bit User Hash + 32-bit Gen Hash + 16-bit CRC16
        """
        body = struct.pack(
            ">BIII",
            version & 0xFF,
            timestamp & 0xFFFFFFFF,
            user_hash & 0xFFFFFFFF,
            gen_hash & 0xFFFFFFFF,
        )
        crc = crc16_ccitt(body)
        data = body + struct.pack(">H", crc)
        bits = list(SYNC_BITS)
        for byte in data:
            for bit_idx in range(7, -1, -1):
                bits.append((byte >> bit_idx) & 1)
        return bits

    def unpack_payload(self, bits: list[int]) -> Optional[dict[str, Any]]:
        """Validates CRC-16 and unpacks 136-bit stream into metadata dictionary."""
        if len(bits) < 136:
            return None
        data_bits = bits[16:136]
        data_bytes = bytearray()
        for i in range(0, len(data_bits), 8):
            byte_val = 0
            for b in data_bits[i : i + 8]:
                byte_val = (byte_val << 1) | (1 if b > 0 else 0)
            data_bytes.append(byte_val)

        body = bytes(data_bytes[:13])
        crc_expected = struct.unpack(">H", bytes(data_bytes[13:15]))[0]
        crc_actual = crc16_ccitt(body)
        if crc_actual != crc_expected:
            logger.debug(f"Acoustic watermark CRC mismatch: expected {crc_expected:04x}, got {crc_actual:04x}")
            return None

        version, timestamp, user_hash, gen_hash = struct.unpack(">BIII", body)
        return {
            "version": version,
            "timestamp": timestamp,
            "user_hash": f"{user_hash:08x}",
            "gen_hash": f"{gen_hash:08x}",
        }

    def _embed_bit_qim(self, val: float, bit: int, delta: float) -> float:
        return float(np.round((val - bit * delta) / (2.0 * delta)) * (2.0 * delta) + bit * delta)

    def _extract_bit_qim(self, val: float, delta: float) -> int:
        rem = val % (2.0 * delta)
        if rem < 0:
            rem += 2.0 * delta
        d0 = min(rem, 2.0 * delta - rem)
        d1 = abs(rem - delta)
        return 0 if d0 < d1 else 1

    def embed_watermark_in_pcm(
        self,
        audio: np.ndarray,
        sample_rate: int,
        version: int,
        timestamp: int,
        user_hash: int,
        gen_hash: int,
    ) -> np.ndarray:
        """
        Embeds acoustic watermark into raw 1D float32 audio waveform.
        Uses Quantization Index Modulation on mid-frequency DCT coefficients.
        """
        out = audio.copy().astype(np.float32)
        bits = self.pack_payload(version, timestamp, user_hash, gen_hash)
        num_bits = len(bits)
        num_frames = len(out) // self.frame_size

        if num_frames < num_bits:
            logger.warning(f"Audio is too short for complete watermark payload ({num_frames} < {num_bits} frames)")
            return out

        bin_idx = int(BIN_CENTER_HZ / (sample_rate / (2 * self.frame_size)))

        for f_idx in range(num_frames):
            bit = bits[f_idx % num_bits]
            start = f_idx * self.frame_size
            end = start + self.frame_size
            frame = out[start:end]

            c = fft.dct(frame, type=2, norm="ortho")
            for b_offset in [-1, 0, 1]:
                b = bin_idx + b_offset
                if 0 <= b < len(c):
                    c[b] = self._embed_bit_qim(c[b], bit, self.delta)

            out[start:end] = fft.idct(c, type=2, norm="ortho")

        return out

    def extract_watermark_from_pcm(self, audio: np.ndarray, sample_rate: int) -> Optional[dict[str, Any]]:
        """
        Extracts acoustic watermark from 1D float32 audio waveform with sync detection & majority voting.
        """
        if sample_rate != self.target_sr:
            # Resample to canonical 24000 Hz if needed
            import librosa

            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=self.target_sr)
            sample_rate = self.target_sr

        num_frames = len(audio) // self.frame_size
        if num_frames < 136:
            logger.debug(f"Audio has fewer frames than single packet ({num_frames} < 136)")
            return None

        bin_idx = int(BIN_CENTER_HZ / (sample_rate / (2 * self.frame_size)))
        raw_bits = []

        for f_idx in range(num_frames):
            start = f_idx * self.frame_size
            end = start + self.frame_size
            frame = audio[start:end]
            c = fft.dct(frame, type=2, norm="ortho")

            decisions = [self._extract_bit_qim(c[bin_idx + b_offset], self.delta) for b_offset in [-1, 0, 1]]
            bit = 1 if sum(decisions) >= 2 else 0
            raw_bits.append(bit)

        # Sync detection: search for Barker sync sequence
        best_offset = -1
        best_matches = -1
        search_limit = min(num_frames - 136 + 1, 136)

        for offset in range(search_limit):
            matches = 0
            p = offset
            count = 0
            while p + 16 <= num_frames:
                matches += sum(1 for i in range(16) if raw_bits[p + i] == SYNC_BITS[i])
                count += 1
                p += 136
            avg_matches = matches / count if count > 0 else 0
            if avg_matches > best_matches:
                best_matches = avg_matches
                best_offset = offset

        # Require at least 13 of 16 sync bits to align
        if best_matches < 13:
            logger.debug(f"Sync word not detected: best_matches={best_matches}")
            return None

        # Majority voting across all repeated packets in the audio stream
        final_bits = []
        for i in range(136):
            votes = []
            p = best_offset + i
            while p < num_frames:
                votes.append(raw_bits[p])
                p += 136
            final_bits.append(1 if sum(votes) > len(votes) / 2 else 0)

        return self.unpack_payload(final_bits)

    def embed_watermark_in_bytes(
        self,
        audio_bytes: bytes,
        owner_id: str,
        generation_id: str,
        timestamp: Optional[int] = None,
        is_mp3: bool = True,
    ) -> tuple[bytes, dict[str, Any]]:
        """
        High-level helper: loads audio bytes, embeds acoustic watermark, and returns
        the watermarked audio encoded as MP3 or WAV bytes alongside the payload dictionary.
        """
        import hashlib
        import time

        ts = int(timestamp or time.time())
        u_hash = int(hashlib.sha256(owner_id.encode("utf-8")).hexdigest()[:8], 16)
        g_hash = int(hashlib.sha256(generation_id.encode("utf-8")).hexdigest()[:8], 16)

        payload_meta = {
            "version": 1,
            "timestamp": ts,
            "user_hash": f"{u_hash:08x}",
            "gen_hash": f"{g_hash:08x}",
            "protocol": "VoiceRep-QIM-HAS-v1",
        }

        # Write input to temp file to read via soundfile / ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_tmp:
            in_wav_path = in_tmp.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wm_tmp:
            wm_wav_path = wm_tmp.name

        out_path = f"/tmp/out_{uuid.uuid4()}" + (".mp3" if is_mp3 else ".wav")

        try:
            # Decode audio to PCM WAV using ffmpeg (handles MP3, AAC, OGG, WAV seamlessly)
            conv_cmd = [
                FFMPEG_BIN,
                "-y",
                "-i", "pipe:0",
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(self.target_sr),
                "-ac", "1",
                in_wav_path,
            ]
            proc = subprocess.run(conv_cmd, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            data, sr = sf.read(in_wav_path)
            if data.ndim > 1:
                data = data[:, 0]

            watermarked_pcm = self.embed_watermark_in_pcm(
                data,
                sample_rate=sr,
                version=1,
                timestamp=ts,
                user_hash=u_hash,
                gen_hash=g_hash,
            )

            sf.write(wm_wav_path, watermarked_pcm, sr)

            if is_mp3:
                # Transcode back to high-bitrate MP3
                mp3_cmd = [
                    FFMPEG_BIN,
                    "-y",
                    "-i", wm_wav_path,
                    "-c:a", "libmp3lame",
                    "-b:a", "256k",
                    "-ar", str(self.target_sr),
                    out_path,
                ]
                subprocess.run(mp3_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                with open(out_path, "rb") as f:
                    output_bytes = f.read()
            else:
                with open(wm_wav_path, "rb") as f:
                    output_bytes = f.read()

            return output_bytes, payload_meta

        finally:
            for p in [in_wav_path, wm_wav_path, out_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    def extract_watermark_from_bytes(self, audio_bytes: bytes) -> Optional[dict[str, Any]]:
        """
        Extracts acoustic watermark directly from media file bytes (MP3, WAV, etc.).
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name

        try:
            conv_cmd = [
                FFMPEG_BIN,
                "-y",
                "-i", "pipe:0",
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(self.target_sr),
                "-ac", "1",
                wav_path,
            ]
            subprocess.run(conv_cmd, input=audio_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            data, sr = sf.read(wav_path)
            if data.ndim > 1:
                data = data[:, 0]
            return self.extract_watermark_from_pcm(data, sample_rate=sr)
        except Exception as e:
            logger.warning(f"Failed to extract acoustic watermark: {e}")
            return None
        finally:
            if os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass


watermark_service = WatermarkService()
