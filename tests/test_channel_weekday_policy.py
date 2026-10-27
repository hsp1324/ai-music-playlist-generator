from collections import Counter
from datetime import date, datetime, timedelta, timezone

import pytest

from app.utils.youtube_schedule_policy import (
    CHANNEL_WEEKDAYS,
    PUBLISH_TIMEZONE,
    is_weekly_slot,
    next_weekly_slot,
    weekday_for_channel,
)


def test_each_weekday_has_a_release_and_only_two_days_have_two_channels():
    assert len(CHANNEL_WEEKDAYS) == 9
    assert Counter(CHANNEL_WEEKDAYS.values()) == {0: 2, 1: 2, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}
    assert 'storylight ost' not in CHANNEL_WEEKDAYS
    assert 'musicsun' not in CHANNEL_WEEKDAYS


@pytest.mark.parametrize('channel,weekday', list(CHANNEL_WEEKDAYS.items()))
def test_channel_slot_has_expected_day_and_lead_time(channel, weekday):
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    slot = next_weekly_slot(now, weekday=weekday_for_channel(channel))
    assert slot.astimezone(PUBLISH_TIMEZONE).weekday() == weekday
    assert slot > now + timedelta(minutes=30)
    assert is_weekly_slot(slot, weekday=weekday)
    assert not is_weekly_slot(slot + timedelta(days=1), weekday=weekday)


def test_known_channel_id_resolves_without_a_title():
    assert weekday_for_channel(None, 'UCc79xOcZwpomZHTb8FaQ1UQ') == 6
    assert weekday_for_channel(None, 'UCKQJOLG6ZBPnI9NOf4rbWVg') == 5


def test_cinematic_lanes_alternate_saturdays_and_skip_occupied_week():
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    orchestra = next_weekly_slot(now, weekday=5, lane='orchestra')
    cute = next_weekly_slot(now, weekday=5, lane='cute_game')
    assert orchestra.date() == date(2026, 10, 24)
    assert cute.date() == date(2026, 10, 31)
    assert not is_weekly_slot(cute, weekday=5, lane='orchestra')
    assert next_weekly_slot(now, weekday=5, lane='orchestra', occupied_dates={orchestra.date()}) == orchestra + timedelta(days=14)


def test_slot_on_lead_boundary_moves_to_next_week():
    now = datetime(2026, 10, 22, 6, 30, tzinfo=PUBLISH_TIMEZONE)
    assert next_weekly_slot(now, weekday=3).date() == date(2026, 10, 29)
