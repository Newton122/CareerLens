"""One definition of "now" for the whole app.

Timestamps are stored as naive UTC: the columns are ``timestamp without time
zone``. ``datetime.utcnow()`` produced exactly that value but is deprecated.
The helper below returns the same value without the warning.

It deliberately strips the time zone rather than returning an aware datetime:
handing PostgreSQL an aware value for a naive column makes it convert using
the database server's own time-zone setting, which would silently shift every
stored time on a server not set to UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """The current time in UTC, without tzinfo (matches the stored columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
