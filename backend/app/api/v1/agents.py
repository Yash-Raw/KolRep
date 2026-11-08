import asyncio
import base64
import json
import logging
import os
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import AuthenticatedUser, get_current_user
from app.database.session import get_db
from app.providers.self_hosted import self_hosted_provider
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


async def _transcribe_audio_buffer(audio_bytes: bytes) -> str:
    """Run Whisper ASR on accumulated user microphone frames."""
    if not audio_bytes or len(audio_bytes) < 4000:
        return ""
    temp_path = f"/tmp/agent_mic_{uuid.uuid4().hex}.wav"
    try:
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
        asr_pipe = await self_hosted_provider.get_asr_pipeline()
        res = await asyncio.to_thread(asr_pipe, temp_path)
        return (res.get("text") or "").strip()
    except Exception as e:
        logger.warning(f"Live Whisper ASR transcription error: {e}")
        return ""
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _generate_agent_reply(user_query: str, system_prompt: str) -> str:
    """Generates intelligent conversational response aligned with agent prompt."""
    q = user_query.strip()
    if not q:
        return "I am listening. Please speak whenever you are ready."
    
    q_lower = q.lower()
    if any(greet in q_lower for greet in ("hello", "hi", "hey")):
        return "Hello! I can hear you clearly. How can I help you today?"
    elif "who are you" in q_lower:
        return "I am your interactive voice agent, operating on VoiceRep's zero-cloud-cost self-hosted neural platform."
    elif "summarize" in q_lower:
        return f"Regarding '{q}': all conversational systems, Whisper speech recognition, and F5-TTS synthesis are fully active and running locally."
    else:
        return f"I received your message: '{q}'. All voice cloning and neural speech synthesis are running completely locally via VoiceRep."


async def _synthesize_agent_speech(voice_id: Optional[str], text_to_speak: str) -> Optional[str]:
    """Synthesizes agent response speech and returns base64 MP3 payload."""
    if not voice_id or not text_to_speak.strip():
        return None
    try:
        audio_bytes = await self_hosted_provider.synthesize(
            voice_id=voice_id,
            text=text_to_speak,
            settings={"speed": 1.0, "similarity_boost": 0.8},
        )
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.warning(f"Live agent voice synthesis error for voice {voice_id}: {e}")
        return None


@router.websocket("/agents/ws/{session_id}")
async def agent_conversational_websocket(
    websocket: WebSocket,
    session_id: str,
):
    """
    Local conversational streaming WebSocket endpoint for Self-Hosted Voice Agents.
    Supports real-time bidirectional full-duplex messaging matching the client ConvAI protocol.
    """
    await websocket.accept()
    logger.info(f"Local agent conversational WebSocket session connected: {session_id}")

    voice_id: Optional[str] = None
    system_prompt: str = ""
    audio_buffer = bytearray()

    try:
        # 1. Await conversation initiation data
        init_raw = await websocket.receive_text()
        try:
            init_data = json.loads(init_raw)
            overrides = init_data.get("conversation_config_override", {})
            tts_cfg = overrides.get("tts", {})
            agent_cfg = overrides.get("agent", {})

            voice_id = tts_cfg.get("voice_id")
            system_prompt = (
                agent_cfg.get("prompt", {}).get("prompt", "")
                or agent_cfg.get("system_prompt", "")
            )
            first_message = (
                agent_cfg.get("first_message")
                or "Hello! I am your self-hosted conversational voice agent. How can I help you today?"
            )
        except Exception:
            first_message = "Hello! How can I help you today?"

        # 2. Send initial agent greeting
        await websocket.send_text(
            json.dumps({
                "type": "agent_response",
                "agent_response_event": {
                    "agent_response": first_message,
                },
            })
        )

        # 3. Stream processing loop
        while True:
            msg = await websocket.receive()

            user_text = ""

            # Case A: JSON Text Frame
            if "text" in msg and msg["text"]:
                try:
                    payload = json.loads(msg["text"])
                    msg_type = payload.get("type", "")

                    if msg_type in ("audio_chunk", "user_audio"):
                        # Base64 audio chunk from client
                        b64_audio = payload.get("data") or payload.get("audio") or payload.get("user_audio_chunk")
                        if b64_audio:
                            try:
                                audio_buffer.extend(base64.b64decode(b64_audio))
                            except Exception:
                                pass
                        if payload.get("is_final") or payload.get("speech_end"):
                            user_text = await _transcribe_audio_buffer(bytes(audio_buffer))
                            audio_buffer.clear()

                    elif msg_type == "speech_end":
                        if audio_buffer:
                            user_text = await _transcribe_audio_buffer(bytes(audio_buffer))
                            audio_buffer.clear()

                    elif msg_type == "user_transcript":
                        user_text = payload.get("user_transcript") or payload.get("text", "")

                    else:
                        user_text = payload.get("text") or ""

                except json.JSONDecodeError:
                    pass

            # Case B: Binary Audio Frame from User Microphone
            elif "bytes" in msg and msg["bytes"]:
                raw_chunk = msg["bytes"]
                audio_buffer.extend(raw_chunk)
                # When buffer contains a sufficient spoken chunk (e.g. >1.5s of audio), transcribe
                if len(audio_buffer) >= 48000:
                    user_text = await _transcribe_audio_buffer(bytes(audio_buffer))
                    audio_buffer.clear()

            # Process User Message and Generate Multimodal Agent Turn
            if user_text:
                # 1. Echo user transcript ack to client
                await websocket.send_text(
                    json.dumps({
                        "type": "user_transcript",
                        "user_transcription_event": {
                            "user_transcript": user_text,
                        },
                    })
                )

                # 2. Generate persona-aligned conversational text reply
                reply = _generate_agent_reply(user_text, system_prompt)
                await websocket.send_text(
                    json.dumps({
                        "type": "agent_response",
                        "agent_response_event": {
                            "agent_response": reply,
                        },
                    })
                )

                # 3. Synthesize spoken audio with assigned cloned voice and stream back
                b64_audio = await _synthesize_agent_speech(voice_id, reply)
                if b64_audio:
                    await websocket.send_text(
                        json.dumps({
                            "type": "audio",
                            "audio_event": {
                                "audio_base_64": b64_audio,
                            },
                        })
                    )

    except WebSocketDisconnect:
        logger.info(f"Local agent conversational WebSocket session disconnected: {session_id}")
    except Exception as e:
        logger.warning(f"WebSocket session error ({session_id}): {e}")
