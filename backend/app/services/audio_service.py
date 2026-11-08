import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional
from app.core.config import settings
from app.schemas.audio import AudioQualityReport

logger = logging.getLogger("voicerep.audio")


def get_binary_path(name: str) -> str:
    # First check standard PATH
    path = shutil.which(name)
    if path:
        return path
    # Check conda environment
    conda_bin = f"/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin/{name}"
    if os.path.exists(conda_bin):
        return conda_bin
    # Check homebrew
    brew_bin = f"/opt/homebrew/bin/{name}"
    if os.path.exists(brew_bin):
        return brew_bin
    return name


FFMPEG_BIN = get_binary_path("ffmpeg")
FFPROBE_BIN = get_binary_path("ffprobe")

ALLOWED_CONTAINERS = {"mp3", "wav", "m4a", "webm", "mp4", "ogg", "flac", "aac", "mov"}


class AudioService:
    def __init__(self):
        self.ffmpeg_path = FFMPEG_BIN
        self.ffprobe_path = FFPROBE_BIN

    def probe_file(self, file_path: str) -> dict:
        """Run ffprobe on file to extract format and stream information."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            raise ValueError("Corrupted or unsupported media file.")
        except Exception as e:
            logger.error(f"Failed to probe file: {e}")
            raise ValueError(f"Could not read audio file metadata: {e}")

    def analyze_audio_stream(self, file_path: str) -> AudioQualityReport:
        """Analyze audio characteristics: duration, sample rate, channels, silence, clipping."""
        info = self.probe_file(file_path)

        format_info = info.get("format", {})
        streams = info.get("streams", [])

        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not audio_stream:
            raise ValueError("No audio stream found in the uploaded file.")

        format_name = format_info.get("format_name", "").lower()
        duration_str = audio_stream.get("duration") or format_info.get("duration")
        if not duration_str:
            raise ValueError("Unable to determine audio duration.")

        duration = float(duration_str)
        sample_rate = int(audio_stream.get("sample_rate", 44100))
        channels = int(audio_stream.get("channels", 1))

        # Check container extension/format against allowed list
        matched_ext = None
        for ext in ALLOWED_CONTAINERS:
            if ext in format_name:
                matched_ext = ext
                break
        detected_format = matched_ext or format_name.split(",")[0].strip()

        warnings: list[str] = []

        # Duration validation (F5-TTS Diffusion Transformer thrives on prime 6-12s audio)
        if duration < 5.0:
            warnings.append("Audio sample is shorter than 5 seconds. Voice cloning may sound inaccurate.")
        elif duration > settings.MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit ({settings.MAX_AUDIO_DURATION_SECONDS}s).")
        elif settings.VOICE_PROVIDER.lower() == "elevenlabs" and duration < 45.0:
            warnings.append("Sample is under 45 seconds. Best results with ElevenLabs are achieved with 60 to 120 seconds of speech.")

        # Sample rate validation
        if sample_rate < 22050:
            warnings.append(f"Low sample rate ({sample_rate} Hz). Audio may lack crispness.")

        # Silence & Volume detection via FFmpeg filters
        silence_duration, max_volume, speech_ratio = self._detect_silence_and_volume(file_path, duration)

        has_clipping = max_volume >= -0.1
        if has_clipping:
            warnings.append("Audio clipping / distortion detected. Volume levels may be peaked.")

        if speech_ratio is not None and speech_ratio < 0.35:
            warnings.append("High amount of silence or low speech activity detected.")

        # Quality scoring (calibrated for diffusion-based zero-shot voice cloning)
        is_self_hosted = settings.VOICE_PROVIDER.lower() == "self_hosted"
        min_good_dur = 6.0 if is_self_hosted else 45.0
        min_acc_dur = 5.0 if is_self_hosted else 15.0

        if duration >= min_good_dur and not has_clipping and (speech_ratio is None or speech_ratio >= 0.45) and not warnings:
            quality = "good"
            recommendation = "Suitable for high-quality instant voice cloning"
            is_clonable = True
        elif duration >= min_acc_dur and (not has_clipping or len(warnings) <= 2):
            quality = "acceptable"
            recommendation = "Acceptable for voice cloning. A clean 6–12s sample is recommended."
            is_clonable = True
        else:
            quality = "poor"
            recommendation = "Low quality or insufficient speech. Please upload or record a clear 6–12s sample."
            is_clonable = duration >= 5.0

        return AudioQualityReport(
            duration_seconds=round(duration, 2),
            format=detected_format,
            sample_rate=sample_rate,
            channels=channels,
            quality=quality,
            speech_ratio=round(speech_ratio, 2) if speech_ratio is not None else None,
            has_clipping=has_clipping,
            warnings=warnings,
            recommendation=recommendation,
            is_clonable=is_clonable,
        )

    def _detect_silence_and_volume(self, file_path: str, duration: float) -> tuple[float, float, Optional[float]]:
        """Run ffmpeg silencedetect and volumedetect filters."""
        cmd = [
            self.ffmpeg_path,
            "-i", file_path,
            "-af", "silencedetect=noise=-30dB:d=0.5,volumedetect",
            "-vn",
            "-f", "null",
            "-",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            output = res.stderr

            # Parse max_volume
            max_volume_match = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", output)
            max_volume = float(max_volume_match.group(1)) if max_volume_match else -6.0

            # Parse silence durations
            silence_starts = [float(x) for x in re.findall(r"silence_start:\s*([\d\.]+)", output)]
            silence_ends = [float(x) for x in re.findall(r"silence_end:\s*([\d\.]+)", output)]

            total_silence = 0.0
            for start, end in zip(silence_starts, silence_ends):
                if end > start:
                    total_silence += (end - start)

            if duration > 0:
                speech_ratio = max(0.0, min(1.0, (duration - total_silence) / duration))
            else:
                speech_ratio = None

            return total_silence, max_volume, speech_ratio
        except Exception as e:
            logger.warning(f"Error analyzing silence/volume: {e}")
            return 0.0, -6.0, None

    def extract_or_convert_to_wav(self, input_path: str, output_path: Optional[str] = None) -> str:
        """Convert input file (including video files like mp4/mov/webm) to a clean 44.1kHz mono WAV file."""
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "1",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
            raise ValueError("Failed to convert audio file.")


audio_service = AudioService()
