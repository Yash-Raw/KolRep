import logging
import uuid
from typing import Optional
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User

logger = logging.getLogger("voicerep.security")
security_scheme = HTTPBearer(auto_error=False)

DEFAULT_LOCAL_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_LOCAL_USER_EMAIL = "local@voicerep.local"


class AuthenticatedUser:
    def __init__(self, user_id: uuid.UUID, email: str):
        self.id = user_id
        self.email = email


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """
    Resolves the authenticated user for local single-user operations.
    In pure local operation, if no credentials are provided or if dev tokens are passed,
    it seamlessly defaults to the local machine owner with zero auth friction.
    """
    user_uuid = DEFAULT_LOCAL_USER_ID
    user_email = DEFAULT_LOCAL_USER_EMAIL

    if credentials and credentials.credentials:
        token = credentials.credentials
        try:
            # Decode token if present without external network round-trips
            payload = jwt.decode(token, options={"verify_signature": False})
            sub = payload.get("sub")
            if sub:
                user_uuid = uuid.UUID(sub)
                user_email = payload.get("email") or f"{str(user_uuid)[:8]}@voicerep.local"
        except Exception as e:
            logger.debug(f"Could not parse custom token, defaulting to local owner: {e}")

    # Ensure user exists in local database
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=user_uuid, email=user_email)
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            refetched = await db.execute(stmt)
            user = refetched.scalar_one_or_none() or User(id=user_uuid, email=user_email)

    return AuthenticatedUser(user_id=user.id, email=user.email)
