"""Datetime utilities — normalize timezone-naive datetimes from SQLite.

SQLite stores all datetimes as naive text strings even when the SQLAlchemy
column declares DateTime(timezone=True).  Any arithmetic between a
timezone-aware ``datetime.now(timezone.utc)`` and a database-loaded value
will crash with "can't subtract offset-naive and offset-aware datetimes".

Use ``ensure_utc()`` at every comparison / subtraction site to guard against
this.
"""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Return *dt* with ``tzinfo=UTC``, or ``None`` if *dt* is ``None``.

    If the datetime is already timezone-aware it is returned unchanged.
    If it is naive (as SQLite returns), UTC is assumed and attached.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
