from typing import Any
from pydantic import BaseModel


class UsageResponse(BaseModel):
    total_voices: int
    ready_voices: int
    total_generations: int
    completed_generations: int
    total_characters_used: int
    recent_activity: list[dict[str, Any]]
