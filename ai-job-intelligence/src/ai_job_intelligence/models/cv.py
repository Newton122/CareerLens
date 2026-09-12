from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    extracted_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    # Structured CandidateProfile, parsed once at upload and cached here as
    # JSON so that every endpoint needing skills does not re-parse the CV.
    # profile_version records which extractor produced it; when the extraction
    # logic changes the stored copy is stale and gets rebuilt on next read.
    profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Semantic embedding of the parsed profile, base64 float32.
    # See services/vector_store.py.
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user = relationship("User", back_populates="cvs")