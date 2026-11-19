import os
import subprocess
import tempfile
import pytest
from app.services.audio_service import audio_service, FFMPEG_BIN


@pytest.fixture(scope="module")
def sample_wav_file():
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    # Generate 15 seconds of 440Hz sine wave tone
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=15",
        "-ar", "44100",
        "-ac", "1",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_probe_valid_file(sample_wav_file):
    info = audio_service.probe_file(sample_wav_file)
    assert "streams" in info
    assert "format" in info
    assert len(info["streams"]) >= 1
    assert info["streams"][0]["codec_type"] == "audio"


def test_analyze_audio_stream(sample_wav_file):
    report = audio_service.analyze_audio_stream(sample_wav_file)
    assert report.duration_seconds >= 14.5
    assert report.sample_rate == 44100
    assert report.channels == 1
    assert report.is_clonable is True
    assert report.format in ("wav", "wav,mp3")


def test_extract_or_convert_to_wav(sample_wav_file):
    converted_path = audio_service.extract_or_convert_to_wav(sample_wav_file)
    assert os.path.exists(converted_path)
    assert converted_path.endswith(".wav")
    info = audio_service.probe_file(converted_path)
    assert info["streams"][0]["sample_rate"] == "44100"
    if os.path.exists(converted_path):
        os.remove(converted_path)


def test_probe_invalid_file():
    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        f.write(b"This is not audio data at all")
        f.flush()
        with pytest.raises(ValueError):
            audio_service.probe_file(f.name)


def test_analyze_streamed_webm_without_header_duration():
    """Verify that streaming WebM (MediaRecorder output with no header duration) is successfully analyzed."""
    fd, path = tempfile.mkstemp(suffix=".webm")
    os.close(fd)
    try:
        # Generate streaming WebM via pipe (no seek back to update EBML duration)
        p = subprocess.Popen(
            [
                FFMPEG_BIN,
                "-y",
                "-f", "lavfi",
                "-i", "sine=frequency=440:duration=8",
                "-c:a", "libopus",
                "-f", "webm",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, _ = p.communicate()
        assert p.returncode == 0
        with open(path, "wb") as f:
            f.write(out)

        # Confirm ffprobe alone cannot find duration in headers
        info = audio_service.probe_file(path)
        format_duration = info.get("format", {}).get("duration")
        audio_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})
        stream_duration = audio_stream.get("duration")
        assert format_duration is None or format_duration == "N/A"
        assert stream_duration is None or stream_duration == "N/A"

        # Our analyze_audio_stream should determine duration using decode fallback
        report = audio_service.analyze_audio_stream(path)
        assert report.duration_seconds >= 7.8 and report.duration_seconds <= 8.2
        assert report.is_clonable is True
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_analyze_fragmented_mp4():
    """Verify that fragmented MP4 (Safari / WebKit MediaRecorder output) is successfully analyzed."""
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        p = subprocess.Popen(
            [
                FFMPEG_BIN,
                "-y",
                "-f", "lavfi",
                "-i", "sine=frequency=440:duration=7",
                "-c:a", "aac",
                "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                "-f", "mp4",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, _ = p.communicate()
        assert p.returncode == 0
        with open(path, "wb") as f:
            f.write(out)

        report = audio_service.analyze_audio_stream(path)
        assert report.duration_seconds >= 6.8 and report.duration_seconds <= 7.2
        assert report.is_clonable is True
    finally:
        if os.path.exists(path):
            os.remove(path)
