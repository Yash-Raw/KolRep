from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    voice_id: uuid.UUID
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: str = Field(..., min_length=10, max_length=5000)
    first_message: str = Field(..., min_length=2, max_length=500)
    language: str = Field(default="en", max_length=32)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    voice_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=10, max_length=5000)
    first_message: Optional[str] = Field(None, min_length=2, max_length=500)
    language: Optional[str] = None
    status: Optional[str] = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    voice_id: uuid.UUID
    name: str
    description: Optional[str] = None
    system_prompt: str
    first_message: str
    language: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int
    page: int
    limit: int


class AgentSessionStartResponse(BaseModel):
    session_id: uuid.UUID
    signed_url: str
    agent_id: str
    session_config: dict[str, Any]
