import asyncio
import io
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.voice import Voice
from app.providers.self_hosted import SelfHostedProvider, normalize_speech_text, self_hosted_provider
from tests.conftest import TEST_USER_ID


@pytest.fixture
def temp_voice_dir(tmp_path):
    orig = settings.SELF_HOSTED_VOICE_DIR
    settings.SELF_HOSTED_VOICE_DIR = str(tmp_path / "voice_profiles")
    provider = SelfHostedProvider()
    yield provider
    settings.SELF_HOSTED_VOICE_DIR = orig


@pytest.fixture
def fake_wav_file(tmp_path):
    wav_path = tmp_path / "test_sample.wav"
    # Create simple WAV header + bytes
    with open(wav_path, "wb") as f:
        f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    return str(wav_path)


@pytest.mark.asyncio
async def test_self_hosted_create_get_delete_voice(temp_voice_dir, fake_wav_file):
    provider = temp_voice_dir

    # 1. Create voice
    res = await provider.create_voice(
        name="Morgan Freeman Clone",
        audio_file_path=fake_wav_file,
        description="A warm, resonant narration voice clone",
    )

    assert "voice_id" in res
    assert res["voice_id"].startswith("self_hosted_")
    assert res["requires_verification"] is False

    voice_id = res["voice_id"]
    profile_dir = Path(settings.SELF_HOSTED_VOICE_DIR) / voice_id
    assert profile_dir.exists()
    assert (profile_dir / "reference.wav").exists()
    assert (profile_dir / "reference.txt").exists()
    assert (profile_dir / "metadata.json").exists()

    # 2. Get voice
    meta = await provider.get_voice(voice_id)
    assert meta["provider_voice_id"] == voice_id
    assert meta["name"] == "Morgan Freeman Clone"
    assert meta["ref_text"] == "A warm, resonant narration voice clone"

    # 3. Create Agent Session
    agent_session = await provider.create_agent_session(
        provider_voice_id=voice_id,
        agent_config={
            "system_prompt": "You are a customer support agent.",
            "first_message": "Hello! How can I assist?",
            "language": "en",
        },
    )
    assert "signed_url" in agent_session
    assert "/api/v1/agents/ws/" in agent_session["signed_url"]
    assert agent_session["session_config"]["overrides"]["tts"]["voice_id"] == voice_id

    # 4. Delete voice
    del_res = await provider.delete_voice(voice_id)
    assert del_res is True
    assert not profile_dir.exists()


@pytest.mark.asyncio
async def test_self_hosted_synthesis_pipeline(temp_voice_dir, fake_wav_file):
    provider = temp_voice_dir

    res = await provider.create_voice(
        name="Studio Voice",
        audio_file_path=fake_wav_file,
    )
    voice_id = res["voice_id"]

    mock_engine = MagicMock()
    mock_engine.infer.return_value = (None, 24000, None)

    with patch.object(provider, "_load_engine_sync", return_value=mock_engine):
        # When infer is called, write a small output file to mimic wav output
        def fake_infer(*args, **kwargs):
            file_wave = kwargs.get("file_wave")
            if file_wave:
                with open(file_wave, "wb") as f:
                    f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
            return None, 24000, None

        mock_engine.infer.side_effect = fake_infer

        audio_bytes = await provider.synthesize(
            voice_id=voice_id,
            text="Welcome to VoiceRep self-hosted narration engine.",
            settings={"speed": 1.0},
        )

        assert isinstance(audio_bytes, bytes)
        assert len(audio_bytes) > 0


def test_agent_conversational_websocket_endpoint():
    """Verify bidirectional streaming protocol over local agent WebSocket."""
    client = TestClient(app)
    session_id = str(uuid.uuid4())

    with client.websocket_connect(f"/api/v1/agents/ws/{session_id}") as ws:
        # Send initiation
        init_payload = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "first_message": "Welcome! I am ready.",
                }
            },
        }
        ws.send_text(json.dumps(init_payload))

        # First message from agent
        data = ws.receive_json()
        assert data["type"] == "agent_response"
        assert data["agent_response_event"]["agent_response"] == "Welcome! I am ready."

        # User sends a transcription event
        user_msg = {
            "type": "user_transcript",
            "user_transcript": "Can you summarize my notifications?",
        }
        ws.send_text(json.dumps(user_msg))

        # Agent returns transcript echo
        transcript_ack = ws.receive_json()
        assert transcript_ack["type"] == "user_transcript"
        assert transcript_ack["user_transcription_event"]["user_transcript"] == "Can you summarize my notifications?"

        # Agent returns response
        agent_reply = ws.receive_json()
        assert agent_reply["type"] == "agent_response"
        assert "summarize my notifications" in agent_reply["agent_response_event"]["agent_response"]


def test_text_normalization():
    raw_text = "Dr. Smith paid $150 (approx. 20%) for AI tools & services"
    normalized = normalize_speech_text(raw_text)
    assert "Doctor" in normalized
    assert "150 dollars" in normalized
    assert "20 percent" in normalized
    assert "and" in normalized
    assert normalized.endswith(".")


@pytest.mark.asyncio
async def test_concurrency_semaphore_race_condition_guard(temp_voice_dir, fake_wav_file):
    """Verify that multiple parallel inference requests queue through the semaphore cleanly."""
    provider = temp_voice_dir
    res = await provider.create_voice(
        name="Concurrent Voice",
        audio_file_path=fake_wav_file,
    )
    voice_id = res["voice_id"]

    active_executions = 0
    max_concurrent_executions = 0

    mock_engine = MagicMock()

    def monitored_fake_infer(*args, **kwargs):
        nonlocal active_executions, max_concurrent_executions
        active_executions += 1
        if active_executions > max_concurrent_executions:
            max_concurrent_executions = active_executions

        file_wave = kwargs.get("file_wave")
        if file_wave:
            with open(file_wave, "wb") as f:
                f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

        # Simulate GPU computation time
        import time
        time.sleep(0.02)
        active_executions -= 1
        return np.zeros(2400, dtype=np.float32), 24000, None

    mock_engine.infer.side_effect = monitored_fake_infer

    with patch.object(provider, "_load_engine_sync", return_value=mock_engine):
        results = await asyncio.gather(
            provider.synthesize(voice_id, "Parallel request one.", {}),
            provider.synthesize(voice_id, "Parallel request two.", {}),
            provider.synthesize(voice_id, "Parallel request three.", {}),
        )

        assert len(results) == 3
        for audio in results:
            assert isinstance(audio, bytes)
            assert len(audio) > 0

        # Concurrency barrier must guarantee sequential thread execution (never > 1)
        assert max_concurrent_executions == 1


@pytest.mark.asyncio
async def test_long_text_phonetic_chunking_and_stitching(temp_voice_dir, fake_wav_file):
    """Verify that long texts (>180 chars) are phonetically split and stitched with silence."""
    from app.providers.self_hosted import chunk_text_by_sentence

    long_paragraph = (
        "VoiceRep features a local zero-cost voice cloning engine built on Diffusion Transformers. "
        "By utilizing Conditional Flow Matching, speech synthesis achieves exceptional acoustic fidelity. "
        "Long passages are split at natural punctuation boundaries, preventing ODE solver degradation and truncation."
    )
    assert len(long_paragraph) > 180

    chunks = chunk_text_by_sentence(long_paragraph, max_chars=180)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 180

    provider = temp_voice_dir
    res = await provider.create_voice(name="Narrator Voice", audio_file_path=fake_wav_file)
    voice_id = res["voice_id"]

    mock_engine = MagicMock()
    def fake_infer(*args, **kwargs):
        file_wave = kwargs.get("file_wave")
        if file_wave:
            with open(file_wave, "wb") as f:
                f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        return np.zeros(2400, dtype=np.float32), 24000, None

    mock_engine.infer.side_effect = fake_infer

    with patch.object(provider, "_load_engine_sync", return_value=mock_engine):
        audio_bytes = await provider.synthesize(voice_id, long_paragraph, {})
        assert isinstance(audio_bytes, bytes)
        assert len(audio_bytes) > 0
        # Engine infer was called once per chunk
        assert mock_engine.infer.call_count == len(chunks)


def test_storage_path_traversal_security_guard():
    """Verify that path traversal attempts are blocked with HTTP 403 Forbidden."""
    client = TestClient(app)

    # 1. Path traversal download attempt (URL encoded to reach the server unnormalized)
    res = client.get("/api/v1/storage/download/%2e%2e/%2e%2e/app/core/config.py")
    assert res.status_code == 403
    assert "Directory traversal" in res.json()["detail"]

    # 2. Path traversal upload attempt
    res2 = client.post(
        "/api/v1/storage/upload/%2e%2e/%2e%2e/evil.txt",
        files={"file": ("evil.txt", b"malicious content", "text/plain")},
    )
    assert res2.status_code == 403
    assert "Directory traversal" in res2.json()["detail"]

    # 3. Direct unit test of get_safe_storage_path
    from app.api.v1.storage import get_safe_storage_path
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        get_safe_storage_path("./storage", "../../app/core/config.py")
    assert exc_info.value.status_code == 403

    # 4. Valid upload and download with HTTP 206 Byte Range support
    valid_key = f"generations/test_{uuid.uuid4().hex}.txt"
    upload_res = client.post(
        f"/api/v1/storage/upload/{valid_key}",
        files={"file": ("test.txt", b"Valid VoiceRep content", "text/plain")},
    )
    assert upload_res.status_code == 200

    download_res = client.get(f"/api/v1/storage/download/{valid_key}")
    assert download_res.status_code == 200
    assert download_res.headers.get("accept-ranges") == "bytes"
    assert download_res.content == b"Valid VoiceRep content"
