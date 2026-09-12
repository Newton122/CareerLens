from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    name = Column(String, nullable=True)
    role = Column(String, default="job_seeker", nullable=False)
    company = Column(String, nullable=True)
    description = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    # Part of every login token (the "ver" claim). Raising it -- after a
    # password reset -- makes every token issued before that moment invalid,
    # which signs the account out on every device. It lives here rather than
    # on ``users`` because the app's database role cannot alter that table on
    # the original development database.
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # When the user clicked the link in their verification email; null until
    # then. Informational: an unverified account can still sign in.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
