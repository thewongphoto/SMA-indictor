"""Portable market refresh targets. Native mobile schedulers call the same jobs.

These are Singapore wall-clock targets, not device-local times or guarantees.
No holiday calendar is inferred from weekdays or absent data.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")
UTC = timezone.utc


JOB_IDS = ("US", "SG", "US_START", "SG_START")


def job_id(region, phase="end"):
    if region not in ("US", "SG") or phase not in ("start", "end"):
        raise ValueError("Choose a US/SG start or end-of-trading job.")
    return region + ("_START" if phase == "start" else "")


def job_details(identifier):
    if identifier not in JOB_IDS:
        raise ValueError("Unknown notification job.")
    return identifier.removesuffix("_START"), "start" if identifier.endswith("_START") else "end"


def schedule_spec(region, phase="end"):
    job_id(region, phase)
    if phase == "start":
        return (21, 30, {0, 1, 2, 3, 4}) if region == "US" else (9, 0, {0, 1, 2, 3, 4})
    if region == "US":
        return (6, 30, {1, 2, 3, 4, 5})
    if region == "SG":
        return (18, 30, {0, 1, 2, 3, 4})
    raise ValueError("Daily background schedules currently support US and Singapore listings.")


def latest_due(region, now, phase="end"):
    hour, minute, weekdays = schedule_spec(region, phase)
    local = now.astimezone(SGT)
    for days in range(8):
        date = local.date() - timedelta(days=days)
        target = datetime(date.year, date.month, date.day, hour, minute, tzinfo=SGT)
        if target.weekday() in weekdays and target <= local:
            return target
    raise ValueError("No schedule found.")


def next_due(region, now, phase="end"):
    hour, minute, weekdays = schedule_spec(region, phase)
    local = now.astimezone(SGT)
    for days in range(8):
        date = local.date() + timedelta(days=days)
        target = datetime(date.year, date.month, date.day, hour, minute, tzinfo=SGT)
        if target.weekday() in weekdays and target > local:
            return target
    raise ValueError("No schedule found.")


def expected_session_date(region, due, phase="end"):
    """A weekday target, not a verified trading day: holidays are deferred."""
    local_date = due.astimezone(SGT).date()
    if phase == "start":
        previous = local_date - timedelta(days=1)
        while previous.weekday() >= 5:
            previous -= timedelta(days=1)
        return previous
    return local_date - timedelta(days=1) if region == "US" else local_date
