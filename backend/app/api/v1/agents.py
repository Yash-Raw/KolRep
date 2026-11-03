import logging
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import AuthenticatedUser, get_current_user
from app.database.session import get_db
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentSessionStartResponse,
    AgentUpdate,
)
from app.services.agent_service import agent_service

logger = logging.getLogger("voicerep.api.agents")
router = APIRouter(tags=["Voice Agents"])


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new conversational AI agent assigned to a cloned voice."""
    agent = await agent_service.create_agent(db, current_user.id, payload)
    return agent


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List AI voice agents owned by user."""
    items, total = await agent_service.get_agents(
        db, current_user.id, page=page, limit=limit
    )
    return AgentListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get details of an AI voice agent."""
    agent = await agent_service.get_agent_by_id(db, agent_id, current_user.id)
    return agent


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update agent configuration, instructions, or voice."""
    agent = await agent_service.update_agent(db, agent_id, current_user.id, payload)
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an AI voice agent."""
    await agent_service.delete_agent(db, agent_id, current_user.id)
    return None


@router.post("/agents/{agent_id}/session", response_model=AgentSessionStartResponse)
async def start_agent_session(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Initiate a live Conversational AI session with signed WebSocket token."""
    res = await agent_service.start_session(db, agent_id, current_user.id)
    return AgentSessionStartResponse(
        session_id=res["session_id"],
        signed_url=res["signed_url"],
        agent_id=res["agent_id"],
        session_config=res["session_config"],
    )
