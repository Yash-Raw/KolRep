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
