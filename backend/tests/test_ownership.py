import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.security import AuthenticatedUser, get_current_user
from app.database.session import get_db
from app.main import app
from app.models.agent import Agent
from app.models.voice import Voice
from tests.conftest import TEST_USER_2_ID, TEST_USER_2_EMAIL, TEST_USER_ID, TEST_USER_EMAIL


@pytest.fixture
async def user_a_voice(db_session):
    voice = Voice(
        id=uuid.uuid4(),
        owner_id=TEST_USER_ID,
        name="User A Secret Voice",
        provider="elevenlabs",
        provider_voice_id="el_secret_1",
        status="ready",
    )
    db_session.add(voice)
    await db_session.commit()
    await db_session.refresh(voice)
    return voice


@pytest.fixture
async def user_a_agent(db_session, user_a_voice):
    agent = Agent(
        id=uuid.uuid4(),
        owner_id=TEST_USER_ID,
        voice_id=user_a_voice.id,
        name="User A Agent",
        system_prompt="Secret instructions",
        first_message="Hi from User A",
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
async def client_user_b(db_session):
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return AuthenticatedUser(user_id=TEST_USER_2_ID, email=TEST_USER_2_EMAIL)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cross_user_voice_isolation(client_user_b, user_a_voice):
    # User B cannot read User A's voice
    res = await client_user_b.get(f"/api/v1/voices/{user_a_voice.id}")
    assert res.status_code == 404

    # User B cannot rename User A's voice
    res = await client_user_b.patch(f"/api/v1/voices/{user_a_voice.id}", json={"name": "Hacked Voice"})
    assert res.status_code == 404

    # User B cannot delete User A's voice
    res = await client_user_b.delete(f"/api/v1/voices/{user_a_voice.id}")
    assert res.status_code == 404

    # User B cannot generate speech using User A's voice
    res = await client_user_b.post(
        "/api/v1/generations",
        json={"voice_id": str(user_a_voice.id), "input_text": "Trying to steal audio"},
    )
    assert res.status_code == 404

    # User B cannot create an agent pointing to User A's voice
    res = await client_user_b.post(
        "/api/v1/agents",
        json={
            "name": "Stolen Voice Agent",
            "voice_id": str(user_a_voice.id),
            "system_prompt": "Test prompt",
            "first_message": "Hello",
        },
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_agent_isolation(client_user_b, user_a_agent):
    # User B cannot read User A's agent
    res = await client_user_b.get(f"/api/v1/agents/{user_a_agent.id}")
    assert res.status_code == 404

    # User B cannot start a session for User A's agent
    res = await client_user_b.post(f"/api/v1/agents/{user_a_agent.id}/session")
    assert res.status_code == 404

    # User B cannot delete User A's agent
    res = await client_user_b.delete(f"/api/v1/agents/{user_a_agent.id}")
    assert res.status_code == 404
