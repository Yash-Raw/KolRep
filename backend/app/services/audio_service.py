import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Optional
from app.core.config import settings
from app.schemas.audio import AudioQualityReport

logger = logging.getLogger("kolrep.audio")


def get_binary_path(name: str) -> str:
    # 1. Check explicit environment override
    env_key = f"KOLREP_{name.upper()}_PATH"
    if os.environ.get(env_key) and os.path.exists(os.environ[env_key]):
        return os.environ[env_key]

    # 2. Check bundled app resources (macOS .app bundle or desktop data dir)
    if hasattr(sys, "executable"):
        exec_dir = Path(sys.executable).resolve().parent
        candidate_paths = [
            exec_dir / "bin" / name,
            exec_dir / name,
            exec_dir.parent / "bin" / name,
            exec_dir.parent / "Resources" / "bin" / name,
            exec_dir.parent / "Resources" / "resources" / "bin" / name,
            exec_dir.parent.parent / "bin" / name,
            exec_dir.parent.parent / "resources" / "bin" / name,
            Path("/Applications/KolRep.app/Contents/Resources/resources/bin") / name,
            Path.home() / "Applications" / "KolRep.app" / "Contents" / "Resources" / "resources" / "bin" / name,
        ]
        for cp in candidate_paths:
            if cp.exists() and os.access(str(cp), os.X_OK):
                return str(cp)

    if settings.DESKTOP_DATA_DIR:
        desktop_bin = Path(settings.DESKTOP_DATA_DIR) / "bin" / name
        if desktop_bin.exists() and os.access(str(desktop_bin), os.X_OK):
            return str(desktop_bin)

    # 3. Check standard PATH
    path = shutil.which(name)
    if path:
        return path
    # 4. Check active or standard conda environments
    conda_candidates = []
    if os.environ.get("CONDA_PREFIX"):
        conda_candidates.append(Path(os.environ["CONDA_PREFIX"]) / "bin" / name)
    conda_candidates.extend([
        Path.home() / "miniforge3" / "envs" / "kolrep" / "bin" / name,
        Path.home() / "miniconda3" / "envs" / "kolrep" / "bin" / name,
        Path(f"/opt/homebrew/Caskroom/miniforge/base/envs/kolrep/bin/{name}"),
    ])
    for conda_bin in conda_candidates:
        if conda_bin.exists():
            return str(conda_bin)
    # 5. Check homebrew
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

    def get_audio_duration(self, file_path: str, audio_stream: dict, format_info: dict) -> float:
        """Extract audio duration using stream/format metadata, tags, or decoding via ffmpeg."""
        # 1. Try format/stream duration metadata if valid float > 0
        for source in (audio_stream.get("duration"), format_info.get("duration")):
            if source is not None and str(source).strip().lower() not in ("n/a", "none", "nan", "inf", ""):
                try:
                    dur = float(source)
                    if dur > 0:
                        return dur
                except (ValueError, TypeError):
                    pass

        # 2. Try duration from stream tags or format tags (e.g. DURATION in Matroska/WebM)
        tags = audio_stream.get("tags") or {}
        format_tags = format_info.get("tags") or {}
        for tag_dict in (tags, format_tags):
            tag_dur = tag_dict.get("DURATION") or tag_dict.get("duration")
            if tag_dur:
                try:
                    dur = float(tag_dur)
                    if dur > 0:
                        return dur
                except ValueError:
                    parts = str(tag_dur).strip().split(":")
                    if len(parts) == 3:
                        try:
                            dur = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                            if dur > 0:
                                return dur
                        except ValueError:
                            pass

        # 3. Fast decode via ffmpeg null muxer to find exact audio duration
        # (Essential for WebM and fragmented MP4 created by browser MediaRecorder where container header lacks duration)
        try:
            cmd = [
                self.ffmpeg_path,
                "-nostats",
                "-i", file_path,
                "-vn",
                "-f", "null",
                "-",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            time_matches = re.findall(r"time=(\d+):(\d+):([\d\.]+)", res.stderr)
            if time_matches:
                h, m, s = time_matches[-1]
                dur = int(h) * 3600 + int(m) * 60 + float(s)
                if dur > 0:
                    return dur
        except Exception as e:
            logger.warning(f"Could not determine duration via ffmpeg decode: {e}")

        # 4. Fallback: Convert to WAV and probe the standardized WAV header
        try:
            temp_wav = self.extract_or_convert_to_wav(file_path)
            try:
                wav_info = self.probe_file(temp_wav)
                wav_format = wav_info.get("format", {})
                wav_stream = next((s for s in wav_info.get("streams", []) if s.get("codec_type") == "audio"), {})
                dur_source = wav_stream.get("duration") or wav_format.get("duration")
                if dur_source is not None and str(dur_source).strip().lower() not in ("n/a", "none", "nan", "inf", ""):
                    dur = float(dur_source)
                    if dur > 0:
                        return dur
            finally:
                if os.path.exists(temp_wav):
                    try:
                        os.remove(temp_wav)
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"Could not determine duration via WAV conversion: {e}")

        raise ValueError("Unable to determine audio duration.")

    def analyze_audio_stream(self, file_path: str) -> AudioQualityReport:
        """Analyze audio characteristics: duration, sample rate, channels, silence, clipping."""
        info = self.probe_file(file_path)

        format_info = info.get("format", {})
        streams = info.get("streams", [])

        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not audio_stream:
            raise ValueError("No audio stream found in the uploaded file.")

        format_name = format_info.get("format_name", "").lower()
        duration = self.get_audio_duration(file_path, audio_stream, format_info)
        sample_rate = int(audio_stream.get("sample_rate") or 44100)
        channels = int(audio_stream.get("channels") or 1)

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
        min_good_dur = 6.0
        min_acc_dur = 5.0

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
