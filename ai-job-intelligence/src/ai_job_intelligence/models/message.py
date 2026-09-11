from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.database import Base


class Message(Base):
    """A direct message between two users.

    There is no separate conversation table: a thread is every message between
    a given pair of users, ordered by time. That keeps sending cheap and makes
    a thread a single indexed query, which is the right trade at this scale.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional context: which job the conversation is about.
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"), nullable=True
    )

    # Null until the recipient opens the thread.
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
