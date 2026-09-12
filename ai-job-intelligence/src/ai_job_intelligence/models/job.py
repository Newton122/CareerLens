from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(255))
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(50), default="full-time")
    required_skills: Mapped[str] = mapped_column(Text, default="[]")
    experience_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(50), default="open")
    company: Mapped[str] = mapped_column(String(255), default="")
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    views: Mapped[int] = mapped_column(Integer, default=0)

    # Semantic embedding of title + skills + description, base64 float32.
    # See services/vector_store.py.
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )

    applications = relationship("Application", back_populates="job")
