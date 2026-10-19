"""One weekly public release per channel; Cinematic Pulse alternates lanes."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PUBLISH_TIMEZONE = ZoneInfo("Asia/Seoul")
CINEMATIC_ORCHESTRA_ANCHOR = date(2026, 10, 21)


def is_weekly_slot(value: datetime, *, lane: str | None = None) -> bool:
    local = value.astimezone(PUBLISH_TIMEZONE)
    if local.weekday() != 2 or (local.hour, local.minute, local.second, local.microsecond) != (7, 0, 0, 0):
        return False
    if lane in {"orchestra", "cute_game"}:
        week = (local.date() - CINEMATIC_ORCHESTRA_ANCHOR).days // 7
        return week % 2 == (0 if lane == "orchestra" else 1)
    return True


def next_weekly_slot(now: datetime, *, lead_minutes: int = 30, lane: str | None = None, occupied_dates=()) -> datetime:
    local = now.astimezone(PUBLISH_TIMEZONE)
    candidate = local.replace(hour=7, minute=0, second=0, microsecond=0)
    candidate += timedelta(days=(2 - candidate.weekday()) % 7)
    cutoff = local + timedelta(minutes=max(lead_minutes, 0))
    occupied = set(occupied_dates)
    while candidate <= cutoff or not is_weekly_slot(candidate, lane=lane) or candidate.date() in occupied:
        candidate += timedelta(days=7)
    return candidate
