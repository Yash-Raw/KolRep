import io
import uuid
import numpy as np
import pytest
import soundfile as sf
from httpx import AsyncClient

from app.services.c2pa_service import c2pa_service
from app.services.watermark_service import watermark_service
from tests.conftest import TEST_USER_ID


@pytest.mark.asyncio
async def test_acoustic_watermark_embed_and_extract():
    # Generate 6 seconds of synthetic audio (optimal for 136-bit watermark frames)
    sr = 24000
    duration = 6.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = (
        0.3 * np.sin(2 * np.pi * 220 * t) +
        0.2 * np.sin(2 * np.pi * 440 * t) +
        0.15 * np.sin(2 * np.pi * 880 * t) +
        0.1 * np.sin(2 * np.pi * 1760 * t) +
        0.05 * np.sin(2 * np.pi * 2500 * t)
    ).astype(np.float32)

    version = 1
    timestamp = 1731234567
    user_hash = 0xA1B2C3D4
    gen_hash = 0xE5F6A7B8

    watermarked = watermark_service.embed_watermark_in_pcm(
        signal,
        sample_rate=sr,
        version=version,
        timestamp=timestamp,
        user_hash=user_hash,
        gen_hash=gen_hash,
    )

    # Check that audio was watermarked with high SNR
    diff = watermarked - signal
    snr = 10 * np.log10(np.mean(signal**2) / (np.mean(diff**2) + 1e-12))
    assert snr > 35.0, f"SNR must be transparent (>35dB), got {snr:.2f}dB"

    # Extract
    extracted = watermark_service.extract_watermark_from_pcm(watermarked, sample_rate=sr)
    assert extracted is not None
    assert extracted["version"] == 1
    assert extracted["timestamp"] == timestamp
    assert extracted["user_hash"] == "a1b2c3d4"
    assert extracted["gen_hash"] == "e5f6a7b8"


@pytest.mark.asyncio
async def test_c2pa_manifest_sign_and_verify():
    audio_dummy = b"test_raw_audio_binary_data"
    gen_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    voice_id = str(uuid.uuid4())

    container_bytes, envelope = c2pa_service.sign_and_embed(
        audio_bytes=audio_dummy,
        generation_id=gen_id,
        owner_id=owner_id,
        voice_id=voice_id,
        model_id="F5TTS_v1_Base",
        is_mp3=True,
    )

    assert container_bytes.startswith(b"ID3")

    # Extract manifest
    extracted = c2pa_service.extract_manifest(container_bytes)
    assert extracted is not None
    assert extracted["manifest"]["instance_id"] == f"urn:uuid:{gen_id}"

    # Verify signature
    is_valid, err = c2pa_service.verify_manifest_signature(extracted)
    assert is_valid is True
    assert err is None

    # Test tamper detection
    tampered_envelope = dict(extracted)
    tampered_envelope["manifest"] = dict(extracted["manifest"])
    tampered_envelope["manifest"]["title"] = "Tampered Audio Title"
    is_tampered_valid, tamper_err = c2pa_service.verify_manifest_signature(tampered_envelope)
    assert is_tampered_valid is False


@pytest.mark.asyncio
async def test_verification_api_endpoints(client: AsyncClient):
    # 1. Test public key endpoint
    pk_resp = await client.get("/api/v1/verify/public-key")
    assert pk_resp.status_code == 200
    assert "-----BEGIN CERTIFICATE-----" in pk_resp.text

    # 2. Test verify endpoint with unwatermarked audio
    sr = 24000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    blank_audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    wav_buf = io.BytesIO()
    sf.write(wav_buf, blank_audio, sr, format="WAV")
    wav_bytes = wav_buf.getvalue()

    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    resp = await client.post("/api/v1/verify", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_authentic"] is False
    assert data["tamper_status"] == "unverified"
    assert data["acoustic_watermark_detected"] is False

    # 3. Test verify endpoint with watermarked & C2PA signed audio
    gen_id = str(uuid.uuid4())
    owner_id = str(TEST_USER_ID)
    voice_id = str(uuid.uuid4())

    # Build 6.5s speech-like audio
    duration = 6.5
    t6 = np.linspace(0, duration, int(sr * duration), endpoint=False)
    speech_signal = (
        0.3 * np.sin(2 * np.pi * 220 * t6) +
        0.2 * np.sin(2 * np.pi * 440 * t6) +
        0.15 * np.sin(2 * np.pi * 880 * t6) +
        0.1 * np.sin(2 * np.pi * 1760 * t6) +
        0.05 * np.sin(2 * np.pi * 2500 * t6)
    ).astype(np.float32)
    s_buf = io.BytesIO()
    sf.write(s_buf, speech_signal, sr, format="WAV")

    wm_bytes, wm_meta = watermark_service.embed_watermark_in_bytes(
        audio_bytes=s_buf.getvalue(),
        owner_id=owner_id,
        generation_id=gen_id,
        is_mp3=True,
    )
    signed_bytes, _ = c2pa_service.sign_and_embed(
        audio_bytes=wm_bytes,
        generation_id=gen_id,
        owner_id=owner_id,
        voice_id=voice_id,
        model_id="F5TTS_v1_Base",
        acoustic_payload=wm_meta,
        is_mp3=True,
    )

    verify_files = {"file": ("signed.mp3", signed_bytes, "audio/mpeg")}
    v_resp = await client.post("/api/v1/verify", files=verify_files)
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["is_authentic"] is True
    assert v_data["c2pa_valid"] is True
    assert v_data["tamper_status"] == "fully_authentic"
    assert v_data["confidence_score"] == 1.0
    assert v_data["model_id"] == "F5TTS_v1_Base"
    assert "EU AI Act Article 50" in " ".join(v_data["compliance"])
