from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    cv_id: Mapped[int] = mapped_column(
        ForeignKey("cvs.id"),
        nullable=False,
    )
    
    job_title = Column(String, nullable=False, default="Untitled Job")
    company = Column(String, nullable=True)

    job_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    match_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    matched_skills: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    missing_skills: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Null means the posting did not state this requirement, so it was not
    # scored. Distinct from 0, which means stated but unmet.
    experience_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    education_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    recommendations: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )