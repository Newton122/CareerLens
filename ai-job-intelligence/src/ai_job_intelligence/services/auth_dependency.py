from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ai_job_intelligence.models.user import User
from ai_job_intelligence.models.user_profile import UserProfile
from ai_job_intelligence.services.auth import (
    SECRET_KEY,
    ALGORITHM,
)
from ai_job_intelligence.services.database import SessionLocal

security = HTTPBearer()

_INVALID = "Invalid authentication token"
_SESSION_ENDED = "Your session has ended. Please sign in again."


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """The id of the signed-in user, or 401.

    The signature and expiry are checked first (no database needed). Then the
    token's ``ver`` claim must match the account's current token_version:
    after a password reset the version goes up, so every token issued before
    the reset is refused. A token for a deleted account is refused too.
    Tokens from before versioning existed carry no ``ver`` and count as 0,
    which is every existing account's starting version.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail=_INVALID)
        user_id = int(user_id)
        token_version = int(payload.get("ver", 0))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail=_INVALID)

    db = SessionLocal()
    try:
        profile = db.get(UserProfile, user_id)
        if profile is None and db.get(User, user_id) is None:
            raise HTTPException(status_code=401, detail=_SESSION_ENDED)
        current_version = (profile.token_version or 0) if profile else 0
    finally:
        db.close()

    if token_version != current_version:
        raise HTTPException(status_code=401, detail=_SESSION_ENDED)

    return user_id
