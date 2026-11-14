from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import AuthenticatedUser, get_current_user
from app.database.session import get_db
from app.models.generation import Generation
from app.models.voice import Voice
from app.schemas.usage import UsageResponse

router = APIRouter(tags=["Usage"])


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve usage statistics and dashboard metrics for the authenticated user."""
    # Voices counts
    v_total_res = await db.execute(
        select(func.count(Voice.id)).where(Voice.owner_id == current_user.id, Voice.deleted_at.is_(None))
    )
    total_voices = v_total_res.scalar() or 0

    v_ready_res = await db.execute(
        select(func.count(Voice.id)).where(
            Voice.owner_id == current_user.id,
            Voice.status == "ready",
            Voice.deleted_at.is_(None),
        )
    )
    ready_voices = v_ready_res.scalar() or 0

    # Generations counts
    g_total_res = await db.execute(
        select(func.count(Generation.id)).where(Generation.owner_id == current_user.id)
    )
    total_generations = g_total_res.scalar() or 0

    g_comp_res = await db.execute(
        select(func.count(Generation.id)).where(
            Generation.owner_id == current_user.id,
            Generation.status == "completed",
        )
    )
    completed_generations = g_comp_res.scalar() or 0

    chars_res = await db.execute(
        select(func.sum(Generation.character_count)).where(
            Generation.owner_id == current_user.id,
            Generation.status == "completed",
        )
    )
    total_characters_used = chars_res.scalar() or 0

    # Recent activity
    recent_gens = await db.execute(
        select(Generation)
        .where(Generation.owner_id == current_user.id)
        .order_by(Generation.created_at.desc())
        .limit(5)
    )
    recent_activity = [
        {
            "type": "generation",
            "id": str(g.id),
            "status": g.status,
            "characters": g.character_count,
            "created_at": g.created_at.isoformat(),
        }
        for g in recent_gens.scalars().all()
    ]

    return UsageResponse(
        total_voices=total_voices,
        ready_voices=ready_voices,
        total_generations=total_generations,
        completed_generations=completed_generations,
        total_characters_used=int(total_characters_used),
        recent_activity=recent_activity,
    )
