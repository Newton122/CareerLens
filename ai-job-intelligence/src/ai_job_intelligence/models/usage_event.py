from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base

# What was used.
USAGE_ANALYSIS = "analysis"
USAGE_CV_UPLOAD = "cv_upload"
USAGE_INSIGHT_SESSION = "insight_session"  # one per 24-hour Career Insights session


class UsageEvent(Base):
    """One use of a metered feature, for plan quotas ("5 analyses a month").

    An append-only ledger rather than a count of ``analyses`` or ``cvs``
    rows. Users can delete analyses and CVs; if the quota counted those rows,
    deleting old ones would hand the month's allowance back. Nothing in the
    app deletes from this table except deleting the whole account.
    """

    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    __table_args__ = (
        # "How many analyses has user X run since the 1st of this month?"
        Index("ix_usage_events_user_kind_created", "user_id", "kind", "created_at"),
    )
