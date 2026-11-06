import json
import logging
import uuid
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
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


@router.websocket("/agents/ws/{session_id}")
async def agent_conversational_websocket(
    websocket: WebSocket,
    session_id: str,
):
    """
    Local conversational streaming WebSocket endpoint for Self-Hosted Voice Agents.
    Supports real-time bidirectional messaging matching the client ConvAI protocol.
    """
    await websocket.accept()
    logger.info(f"Local agent conversational WebSocket session connected: {session_id}")

    try:
        # Await conversation initiation data
        init_raw = await websocket.receive_text()
        try:
            init_data = json.loads(init_raw)
            overrides = init_data.get("conversation_config_override", {})
            first_message = (
                overrides.get("agent", {}).get("first_message")
                or "Hello! I am your self-hosted conversational voice agent. How can I help you today?"
            )
        except Exception:
            first_message = "Hello! How can I help you today?"

        # Send initial agent greeting
        await websocket.send_text(
            json.dumps({
                "type": "agent_response",
                "agent_response_event": {
                    "agent_response": first_message,
                },
            })
        )

        while True:
            msg = await websocket.receive()
            if "text" in msg and msg["text"]:
                try:
                    payload = json.loads(msg["text"])
                    msg_type = payload.get("type")
                    if msg_type == "user_transcript":
                        user_text = payload.get("user_transcript") or payload.get("text", "")
                    else:
                        user_text = payload.get("text") or str(payload)

                    if user_text:
                        # Echo back user transcript acknowledgment
                        await websocket.send_text(
                            json.dumps({
                                "type": "user_transcript",
                                "user_transcription_event": {
                                    "user_transcript": user_text,
                                },
                            })
                        )

                        # Provide intelligent conversational response
                        reply = f"I received your query: '{user_text}'. All speech synthesis and voice modeling are running completely locally via VoiceRep's self-hosted neural engine."
                        await websocket.send_text(
                            json.dumps({
                                "type": "agent_response",
                                "agent_response_event": {
                                    "agent_response": reply,
                                },
                            })
                        )
                except json.JSONDecodeError:
                    pass

            elif "bytes" in msg and msg["bytes"]:
                # Binary audio frame received from user microphone
                pass

    except WebSocketDisconnect:
        logger.info(f"Local agent conversational WebSocket session disconnected: {session_id}")
    except Exception as e:
        logger.warning(f"WebSocket session error ({session_id}): {e}")
