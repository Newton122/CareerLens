from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="applied",
        nullable=False,
    )
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )

    job = relationship("Job", back_populates="applications")
