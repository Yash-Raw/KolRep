import io
import subprocess
import tempfile
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from app.models.voice import Voice
from app.models.voice_consent import VoiceConsent
from app.services.audio_service import FFMPEG_BIN
from tests.conftest import TEST_USER_2_ID, TEST_USER_ID


@pytest.fixture(scope="module")
def sample_audio_bytes():
    fd, path = tempfile.mkstemp(suffix=".wav")
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
    with open(path, "rb") as f:
        data = f.read()
    subprocess.run(["rm", "-f", path])
    return data


@pytest.mark.asyncio
async def test_create_voice_flow(client, sample_audio_bytes):
    mock_provider_res = {"voice_id": "self_hosted_voice_123", "requires_verification": False}

    with patch("app.services.voice_service.self_hosted_provider.create_voice", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_provider_res

        files = {"file": ("test_voice.wav", io.BytesIO(sample_audio_bytes), "audio/wav")}
        data = {
            "name": "Sarah Persona",
            "language": "en",
            "speaker_relationship": "self",
            "terms_accepted": "true",
        }

        response = await client.post("/api/v1/voices", data=data, files=files)
        assert response.status_code == 201
        res_json = response.json()
        assert res_json["name"] == "Sarah Persona"
        assert res_json["status"] == "ready"
        assert res_json["provider_voice_id"] == "self_hosted_voice_123"
        voice_id = res_json["id"]

        # Verify listing
        list_res = await client.get("/api/v1/voices")
        assert list_res.status_code == 200
        list_json = list_res.json()
        assert list_json["total"] >= 1
        assert any(v["id"] == voice_id for v in list_json["items"])

        # Verify get by ID
        get_res = await client.get(f"/api/v1/voices/{voice_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Sarah Persona"

        # Verify update
        patch_res = await client.patch(f"/api/v1/voices/{voice_id}", json={"name": "Sarah Voice Clone V2"})
        assert patch_res.status_code == 200
        assert patch_res.json()["name"] == "Sarah Voice Clone V2"

        # Verify delete
        with patch("app.services.voice_service.self_hosted_provider.delete_voice", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = True
            del_res = await client.delete(f"/api/v1/voices/{voice_id}")
            assert del_res.status_code == 204

        # Verify voice is deleted
        get_again = await client.get(f"/api/v1/voices/{voice_id}")
        assert get_again.status_code == 404


@pytest.mark.asyncio
async def test_voice_requires_terms(client, sample_audio_bytes):
    files = {"file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")}
    data = {
        "name": "Terms Test",
        "terms_accepted": "false",
    }
    response = await client.post("/api/v1/voices", data=data, files=files)
    assert response.status_code in (400, 422)
