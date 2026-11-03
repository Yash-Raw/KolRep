import logging
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User

logger = logging.getLogger("voicerep.security")
security_scheme = HTTPBearer(auto_error=False)

# Cache JWK client if URL configured
_jwks_client: Optional[PyJWKClient] = None
if settings.SUPABASE_JWKS_URL:
    try:
        _jwks_client = PyJWKClient(settings.SUPABASE_JWKS_URL)
    except Exception as e:
        logger.warning(f"Could not initialize JWKS client: {e}")


class AuthenticatedUser:
    def __init__(self, user_id: uuid.UUID, email: str):
        self.id = user_id
        self.email = email


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> AuthenticatedUser:
    if not credentials or not credentials.credentials:
        # Check if running in dev and fallback header exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id_str: Optional[str] = None
    email: Optional[str] = None

    try:
        if settings.SUPABASE_JWKS_URL and _jwks_client:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience="authenticated",
                options={"verify_aud": True}
            )
            user_id_str = payload.get("sub")
            email = payload.get("email")
        elif settings.SUPABASE_JWT_SECRET:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": False}
            )
            user_id_str = payload.get("sub")
            email = payload.get("email")
        else:
            # In development/test mode without live Supabase credentials,
            # allow decoding without signature verification
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication provider not configured for production",
                )
            # Try to decode unverified payload
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id_str = payload.get("sub")
            email = payload.get("email", "dev@voicerep.local")

        if not user_id_str:
            raise ValueError("Token missing 'sub' claim")

        user_uuid = uuid.UUID(user_id_str)
        user_email = email or f"{user_id_str[:8]}@voicerep.local"

    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure user exists in our local database
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=user_uuid, email=user_email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return AuthenticatedUser(user_id=user.id, email=user.email)
