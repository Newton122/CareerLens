from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base

# How the two sides actually meet. Stored rather than inferred from the
# presence of a link, because "phone" and "on-site" are real choices an
# employer makes, not the absence of a video call.
INTERVIEW_MODES = ("video", "phone", "onsite")

DEFAULT_DURATION_MINUTES = 45


class Interview(Base):
    """An interview an employer has scheduled with a candidate.

    Addressed by user id on both sides. ``cv_id`` records which CV the employer
    was looking at when they scheduled it, which is context rather than
    identity -- a candidate may upload another CV later without invalidating
    an already-booked interview.

    The joining details (``mode`` through ``timezone``) are what turn a row in
    this table into something a candidate can actually attend. Before they
    existed the only pointer was a free-text ``location``, so a video call had
    nowhere to put its link and the candidate had no way to reach the employer
    if anything went wrong.
    """

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    employer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    candidate_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    cv_id: Mapped[int | None] = mapped_column(
        ForeignKey("cvs.id"), nullable=True
    )
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"), nullable=True
    )

    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # scheduled -> confirmed | declined | cancelled | completed
    status: Mapped[str] = mapped_column(
        String(30), default="scheduled", nullable=False
    )

    # --- How to attend -------------------------------------------------
    # One of INTERVIEW_MODES. Defaults to video: it is both the common case
    # and the one that needs a link, so the form has something to ask for.
    mode: Mapped[str] = mapped_column(
        String(20), default="video", nullable=False
    )

    # Only ever an http/https URL -- validated on the way in, because this is
    # rendered as a link and a "javascript:" value would run in the
    # candidate's browser. See _clean_meeting_url in main.py.
    meeting_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fallback number for a video call that will not connect, and the primary
    # channel when mode is "phone".
    dial_in: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Who to contact when something goes wrong on the day. Kept on the
    # interview rather than read off the employer's profile so an employer can
    # route one interview to a specific hiring manager.
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    duration_minutes: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_DURATION_MINUTES, nullable=False
    )

    # IANA name, e.g. "Africa/Nairobi". scheduled_at is stored naive-UTC, so
    # this records the zone the employer was thinking in when they picked the
    # time -- enough to show "3:00 PM EAT" rather than a bare timestamp.
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Street address or room. Meaningful for mode="onsite".
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
