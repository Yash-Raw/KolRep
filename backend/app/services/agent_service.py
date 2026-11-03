import logging
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent import Agent
from app.models.agent_session import AgentSession
from app.models.voice import Voice
from app.providers.elevenlabs import elevenlabs_provider
from app.schemas.agent import AgentCreate, AgentUpdate

logger = logging.getLogger("voicerep.agent_service")


class AgentService:
    async def create_agent(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: AgentCreate,
    ) -> Agent:
        # Validate voice ownership and ready status
        voice_query = select(Voice).where(
            Voice.id == payload.voice_id,
            Voice.owner_id == owner_id,
            Voice.deleted_at.is_(None),
        )
        voice_res = await db.execute(voice_query)
        voice = voice_res.scalar_one_or_none()
        if not voice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected voice profile not found or access denied.",
            )

        if voice.status != "ready" or not voice.provider_voice_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Voice is not ready for agent assignment (status: {voice.status}).",
            )

        agent = Agent(
            id=uuid.uuid4(),
            owner_id=owner_id,
            voice_id=voice.id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            system_prompt=payload.system_prompt.strip(),
            first_message=payload.first_message.strip(),
            language=payload.language or "en",
            status="active",
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent

    async def get_agents(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Agent], int]:
        offset = (page - 1) * limit
        query = (
            select(Agent)
            .where(Agent.owner_id == owner_id)
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count(Agent.id)).where(Agent.owner_id == owner_id)

        res = await db.execute(query)
        items = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_agent_by_id(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Agent:
        query = select(Agent).where(
            Agent.id == agent_id,
            Agent.owner_id == owner_id,
        )
        res = await db.execute(query)
        agent = res.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or access denied.",
            )
        return agent

    async def update_agent(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        owner_id: uuid.UUID,
        payload: AgentUpdate,
    ) -> Agent:
        agent = await self.get_agent_by_id(db, agent_id, owner_id)

        if payload.voice_id is not None and payload.voice_id != agent.voice_id:
            voice_query = select(Voice).where(
                Voice.id == payload.voice_id,
                Voice.owner_id == owner_id,
                Voice.deleted_at.is_(None),
            )
            v_res = await db.execute(voice_query)
            voice = v_res.scalar_one_or_none()
            if not voice or voice.status != "ready":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Replacement voice not found or not in 'ready' status.",
                )
            agent.voice_id = voice.id

        if payload.name is not None:
            agent.name = payload.name.strip()
        if payload.description is not None:
            agent.description = payload.description.strip()
        if payload.system_prompt is not None:
            agent.system_prompt = payload.system_prompt.strip()
        if payload.first_message is not None:
            agent.first_message = payload.first_message.strip()
        if payload.language is not None:
            agent.language = payload.language
        if payload.status is not None:
            agent.status = payload.status

        await db.commit()
        await db.refresh(agent)
        return agent

    async def delete_agent(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> bool:
        agent = await self.get_agent_by_id(db, agent_id, owner_id)
        await db.delete(agent)
        await db.commit()
        return True

    async def start_session(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> dict:
        agent = await self.get_agent_by_id(db, agent_id, owner_id)

        # Retrieve voice
        voice_query = select(Voice).where(
            Voice.id == agent.voice_id,
            Voice.deleted_at.is_(None),
        )
        voice_res = await db.execute(voice_query)
        voice = voice_res.scalar_one_or_none()
        if not voice or voice.status != "ready" or not voice.provider_voice_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned voice profile is not ready for live conversation.",
            )

        # Create AgentSession record
        session = AgentSession(
            id=uuid.uuid4(),
            owner_id=owner_id,
            agent_id=agent.id,
            status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Get signed ConvAI URL from ElevenLabs
        try:
            conv_data = await elevenlabs_provider.create_agent_session(
                provider_voice_id=voice.provider_voice_id,
                agent_config={
                    "system_prompt": agent.system_prompt,
                    "first_message": agent.first_message,
                    "language": agent.language,
                },
            )
        except Exception as e:
            logger.error(f"Failed to initiate agent session: {e}")
            session.status = "failed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Conversational AI provider error: {str(e)}",
            )

        return {
            "session_id": session.id,
            "signed_url": conv_data["signed_url"],
            "agent_id": conv_data["agent_id"],
            "session_config": conv_data["session_config"],
        }


agent_service = AgentService()
