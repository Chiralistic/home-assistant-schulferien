"""Bounded retries and explicit data quality for holiday calendars."""
from datetime import timedelta
from .const import DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE


def validate_records(data):
    """Reject incomplete calendars before the parser can skip invalid rows."""
    for row in data:
        if not isinstance(row, dict) or not row.get("startDate") or not row.get("endDate"):
            raise ValueError("Unvollständiger Ferienzeitraum")
        if row["startDate"] > row["endDate"]:
            raise ValueError("Ungültiger Ferienzeitraum")


class FetchState:
    """Keep failed/empty responses distinct from a known non-holiday day."""

    def __init__(self):
        self.status = "not_loaded"
        self.failures = 0
        self.retry_at = None
        self.valid_until = None
        self.in_progress = False

    def failed(self, now, *, empty=False):
        """Retry startup failures promptly without retrying every entity poll."""
        self.status = "no_data" if empty else "error"
        self.failures += 1
        minutes = 1440 if empty else (1, 5, 15, 60, 360)[min(self.failures - 1, 4)]
        self.retry_at = now + timedelta(minutes=minutes)

    def succeeded(self, valid_until):
        """A validated, nonempty calendar establishes the covered time range."""
        self.status = "ok"
        self.failures = 0
        self.retry_at = None
        self.valid_until = valid_until

    def available_on(self, day):
        """Never present missing data as a confirmed non-holiday."""
        return self.status == "ok" and self.valid_until is not None and day <= self.valid_until

    def due(self, now, last_success, last_attempt):
        """Failures back off; successful calendars keep the weekly 03:00 cadence."""
        if self.in_progress:
            return False
        if self.retry_at is not None:
            return now >= self.retry_at
        if last_success is None:
            return last_attempt is None or now - last_attempt >= timedelta(minutes=1)
        return (
            (now.date() - last_success.date()).days >= 7
            and (now.hour, now.minute) >= (DAILY_UPDATE_HOUR, DAILY_UPDATE_MINUTE)
        )

    @property
    def attributes(self):
        """Expose failure and recovery timing without claiming no holidays."""
        return {
            "data_status": self.status,
            "next_retry": self.retry_at.isoformat() if self.retry_at else None,
            "data_valid_until": self.valid_until.isoformat() if self.valid_until else None,
        }
