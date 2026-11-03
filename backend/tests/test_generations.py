import uuid
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from app.models.voice import Voice
from tests.conftest import TEST_USER_ID


@pytest_asyncio.fixture
async def ready_voice(db_session):
    voice = Voice(
        id=uuid.uuid4(),
        owner_id=TEST_USER_ID,
        name="Alex Narrator",
        provider="elevenlabs",
        provider_voice_id="el_alex_999",
        status="ready",
        language="en",
        audio_duration=65.0,
    )
    db_session.add(voice)
    await db_session.commit()
    await db_session.refresh(voice)
    return voice


@pytest.mark.asyncio
async def test_generation_flow(client, ready_voice):
    fake_mp3_bytes = b"ID3\x03\x00\x00\x00\x00\x00\x00dummy_audio_bytes"

    with patch("app.services.studio_service.elevenlabs_provider.synthesize", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = fake_mp3_bytes

        payload = {
            "voice_id": str(ready_voice.id),
            "input_text": "Hello, welcome to VoiceRep narration studio.",
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "speed": 1.0,
                "style": 0.0,
            },
        }

        response = await client.post("/api/v1/generations", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert data["character_count"] == len(payload["input_text"])
        assert data["audio_url"] is not None
        gen_id = data["id"]

        # Verify list
        list_res = await client.get("/api/v1/generations")
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert any(item["id"] == gen_id for item in items)

        # Verify audio endpoint
        audio_res = await client.get(f"/api/v1/generations/{gen_id}/audio")
        assert audio_res.status_code == 200
        assert "audio_url" in audio_res.json()

        # Verify deletion
        del_res = await client.delete(f"/api/v1/generations/{gen_id}")
        assert del_res.status_code == 204

        # Verify gone
        get_again = await client.get(f"/api/v1/generations/{gen_id}")
        assert get_again.status_code == 404


@pytest.mark.asyncio
async def test_generation_rejects_unready_voice(client, db_session):
    unready_voice = Voice(
        id=uuid.uuid4(),
        owner_id=TEST_USER_ID,
        name="Processing Voice",
        provider="elevenlabs",
        status="cloning",
    )
    db_session.add(unready_voice)
    await db_session.commit()

    payload = {
        "voice_id": str(unready_voice.id),
        "input_text": "Should fail because voice is not ready.",
    }
    response = await client.post("/api/v1/generations", json=payload)
    assert response.status_code == 400
    assert "not ready" in response.json()["detail"].lower()
