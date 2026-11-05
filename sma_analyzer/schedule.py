"""Portable market refresh targets. Native mobile schedulers call the same jobs.

These are Singapore wall-clock targets, not device-local times or guarantees.
No holiday calendar is inferred from weekdays or absent data.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")
UTC = timezone.utc


def schedule_spec(region):
    if region == "US":
        return (6, 0, {1, 2, 3, 4, 5})
    if region == "SG":
        return (17, 30, {0, 1, 2, 3, 4})
    raise ValueError("Daily background schedules currently support US and Singapore listings.")


def latest_due(region, now):
    hour, minute, weekdays = schedule_spec(region)
    local = now.astimezone(SGT)
    for days in range(8):
        date = local.date() - timedelta(days=days)
        target = datetime(date.year, date.month, date.day, hour, minute, tzinfo=SGT)
        if target.weekday() in weekdays and target <= local:
            return target
    raise ValueError("No schedule found.")


def next_due(region, now):
    hour, minute, weekdays = schedule_spec(region)
    local = now.astimezone(SGT)
    for days in range(8):
        date = local.date() + timedelta(days=days)
        target = datetime(date.year, date.month, date.day, hour, minute, tzinfo=SGT)
        if target.weekday() in weekdays and target > local:
            return target
    raise ValueError("No schedule found.")


def expected_session_date(region, due):
    """A weekday target, not a verified trading day: holidays are deferred."""
    local_date = due.astimezone(SGT).date()
    return local_date - timedelta(days=1) if region == "US" else local_date
