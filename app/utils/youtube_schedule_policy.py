"""Weekly YouTube release times by channel, in Korea time."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PUBLISH_TIMEZONE = ZoneInfo("Asia/Seoul")
# Pairs spread the nine automated channels as evenly as possible across seven days.
CHANNEL_WEEKDAYS = {
    "haruharu": 0, "불송": 0,
    "solwave radio": 1, "bibliacanto": 1,
    "tokyo daydream radio": 2,
    "soft hour radio": 3,
    "sundaze": 4,
    "cinematic pulse": 5,
    "club bloom": 6,
}
CHANNEL_IDS = {
    "UCLEr6COc_lUUgvL27gyVTNg": "haruharu",
    "UCMDveEHZHOEnFOYxvfyYICQ": "불송",
    "UC-kzdY8OWXlXB5siplXvp4g": "solwave radio",
    "UCSnvMyapZRZTJvWJGhkK4AA": "bibliacanto",
    "UCUpTHfTl_tgHS1rFtSQU7CA": "tokyo daydream radio",
    "UCvBgTYRROhe3WQBgYRiNUcQ": "soft hour radio",
    "UCQh5O10XfZLLNZqdGuQR7Jw": "sundaze",
    "UCKQJOLG6ZBPnI9NOf4rbWVg": "cinematic pulse",
    "UCc79xOcZwpomZHTb8FaQ1UQ": "club bloom",
}
CINEMATIC_ORCHESTRA_ANCHOR = date(2026, 10, 21)  # original orchestra week


def weekday_for_channel(title: str | None = None, channel_id: str | None = None) -> int:
    key = CHANNEL_IDS.get(str(channel_id or "").strip()) or str(title or "").strip().casefold()
    key = {"the old verse": "bibliacanto", "old verse": "bibliacanto", "biblia canto": "bibliacanto", "the new verse": "불송", "new verse": "불송", "bulsong": "불송"}.get(key, key)
    return CHANNEL_WEEKDAYS.get(key, 2)


def is_weekly_slot(value: datetime, *, lane: str | None = None, weekday: int = 2) -> bool:
    local = value.astimezone(PUBLISH_TIMEZONE)
    if local.weekday() != weekday or (local.hour, local.minute, local.second, local.microsecond) != (7, 0, 0, 0):
        return False
    if lane in {"orchestra", "cute_game"}:
        anchor = CINEMATIC_ORCHESTRA_ANCHOR + timedelta(days=weekday - 2)
        week = (local.date() - anchor).days // 7
        return week % 2 == (0 if lane == "orchestra" else 1)
    return True


def next_weekly_slot(now: datetime, *, lead_minutes: int = 30, lane: str | None = None, occupied_dates=(), weekday: int = 2) -> datetime:
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be in 0..6")
    local = now.astimezone(PUBLISH_TIMEZONE)
    candidate = local.replace(hour=7, minute=0, second=0, microsecond=0)
    candidate += timedelta(days=(weekday - candidate.weekday()) % 7)
    cutoff = local + timedelta(minutes=max(lead_minutes, 0))
    occupied = set(occupied_dates)
    while candidate <= cutoff or not is_weekly_slot(candidate, lane=lane, weekday=weekday) or candidate.date() in occupied:
        candidate += timedelta(days=7)
    return candidate
