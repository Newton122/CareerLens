from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base

# What a token is for. Each purpose is checked separately, so a verification
# link can never be used to reset a password.
PURPOSE_PASSWORD_RESET = "password_reset"
PURPOSE_VERIFY_EMAIL = "verify_email"


class AuthToken(Base):
    """A one-time link sent by email: password reset or email verification.

    Only a SHA-256 hash of the token is stored, never the token itself -- the
    same idea as storing password hashes. Someone who reads this table (a
    leaked backup, say) cannot turn a row back into a working link.
    """

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Set when the link is used; a used token never works again.
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
