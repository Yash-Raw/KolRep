import uuid
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from app.models.voice import Voice
from tests.conftest import TEST_USER_ID


@pytest_asyncio.fixture
async def agent_ready_voice(db_session):
    voice = Voice(
        id=uuid.uuid4(),
        owner_id=TEST_USER_ID,
        name="Cloned Assistant Voice",
        provider="elevenlabs",
        provider_voice_id="el_convai_voice_888",
        status="ready",
        language="en",
        audio_duration=75.0,
    )
    db_session.add(voice)
    await db_session.commit()
    await db_session.refresh(voice)
    return voice


@pytest.mark.asyncio
async def test_agent_lifecycle_and_session(client, agent_ready_voice):
    create_payload = {
        "name": "Research Buddy",
        "voice_id": str(agent_ready_voice.id),
        "description": "Assists with technical deep-dives",
        "system_prompt": "You are a concise research specialist. Answer directly and precisely.",
        "first_message": "Hello! How can I assist with your research today?",
        "language": "en",
    }

    # Create agent
    response = await client.post("/api/v1/agents", json=create_payload)
    assert response.status_code == 201
    agent_data = response.json()
    assert agent_data["name"] == "Research Buddy"
    assert agent_data["status"] == "active"
    agent_id = agent_data["id"]

    # List agents
    list_res = await client.get("/api/v1/agents")
    assert list_res.status_code == 200
    assert any(a["id"] == agent_id for a in list_res.json()["items"])

    # Update agent
    patch_res = await client.patch(
        f"/api/v1/agents/{agent_id}",
        json={"name": "Senior Research Buddy", "description": "Updated description"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Senior Research Buddy"

    # Start session
    mock_session_res = {
        "signed_url": "wss://api.elevenlabs.io/v1/convai/conversation?token=signed_jwt_token_here",
        "agent_id": "mock_agent_id",
        "session_config": {
            "agent_id": "mock_agent_id",
            "overrides": {
                "tts": {"voice_id": "el_convai_voice_888"},
                "agent": {
                    "prompt": {"prompt": "You are a concise research specialist. Answer directly and precisely."},
                    "first_message": "Hello! How can I assist with your research today?",
                    "language": "en",
                },
            },
        },
    }

    with patch("app.services.agent_service.elevenlabs_provider.create_agent_session", new_callable=AsyncMock) as mock_conv:
        mock_conv.return_value = mock_session_res

        session_res = await client.post(f"/api/v1/agents/{agent_id}/session")
        assert session_res.status_code == 200
        sess_data = session_res.json()
        assert "session_id" in sess_data
        assert "signed_url" in sess_data
        assert sess_data["signed_url"].startswith("wss://")
        assert sess_data["session_config"]["overrides"]["tts"]["voice_id"] == "el_convai_voice_888"

    # Delete agent
    del_res = await client.delete(f"/api/v1/agents/{agent_id}")
    assert del_res.status_code == 204

    # Verify deleted
    get_again = await client.get(f"/api/v1/agents/{agent_id}")
    assert get_again.status_code == 404
