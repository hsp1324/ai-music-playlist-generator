from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.utils.youtube_schedule_policy import is_weekly_slot, next_weekly_slot
from app.workflows.playlist_automation import next_youtube_scheduled_publish_at, youtube_schedule_options_for_playlist
from app.models.playlist import Playlist

KST = ZoneInfo('Asia/Seoul')
NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)


@pytest.mark.parametrize('channel', ['HaruHaru', 'Tokyo Daydream Radio', 'sundaze', 'Solwave Radio', 'Club Bloom', 'Soft Hour Radio', 'BibliaCanto', '불송', 'MusicSun', 'Custom Channel'])
def test_every_channel_gets_one_wednesday_slot(channel):
    options = youtube_schedule_options_for_playlist(Playlist(title='test', metadata_json={'target_youtube_channel_title': channel}))
    assert (options['schedule_hour'], options['schedule_minute'], options['schedule_interval_days'], options['schedule_scope']) == (7, 0, 7, 'date')
    assert next_weekly_slot(NOW) == datetime(2026, 10, 21, 7, tzinfo=KST)


def test_cinematic_alternates_without_sharing_a_date():
    assert next_weekly_slot(NOW, lane='orchestra') == datetime(2026, 10, 21, 7, tzinfo=KST)
    assert next_weekly_slot(NOW, lane='cute_game') == datetime(2026, 10, 28, 7, tzinfo=KST)
    assert next_weekly_slot(datetime(2026,10,22,tzinfo=KST), lane='orchestra') == datetime(2026,11,4,7,tzinfo=KST)
    assert next_weekly_slot(NOW, lane='cute_game', occupied_dates={datetime(2026,10,28).date()}) == datetime(2026,11,11,7,tzinfo=KST)


@pytest.mark.parametrize('minute,day', [(29,21),(30,28),(31,28)])
def test_lead_time_boundary(minute,day):
    now=datetime(2026,10,21,6,minute,tzinfo=KST)
    assert next_weekly_slot(now).day == day


def test_cinematic_requires_a_known_lane():
    with pytest.raises(ValueError, match='needs an orchestra or cute_game lane'):
        youtube_schedule_options_for_playlist(Playlist(title='Unknown', metadata_json={'target_youtube_channel_title':'Cinematic Pulse'}))


def test_database_scheduler_shares_channel_slot_and_ignores_legacy_hours():
    scheduled=Playlist(id='occupied',title='Game',metadata_json={'youtube_channel_id':'A','youtube_scheduled_publish_at':'2026-10-20T22:00:00Z'})
    other=Playlist(id='other',title='Other',metadata_json={'youtube_channel_id':'B','youtube_scheduled_publish_at':'2026-10-27T22:00:00Z'})
    class DB:
        def scalars(self,*args): return SimpleNamespace(all=lambda:[scheduled,other])
    services=SimpleNamespace(settings=SimpleNamespace(youtube_schedule_public_enabled=True,youtube_schedule_min_lead_minutes=30))
    result=next_youtube_scheduled_publish_at(DB(),services,youtube_channel_id='A',now=NOW,schedule_hour=19,schedule_scope='slot')
    assert result == datetime(2026,10,27,22,tzinfo=timezone.utc)
    result=next_youtube_scheduled_publish_at(DB(),services,youtube_channel_id='A',now=NOW,exclude_playlist_id='occupied')
    assert result == datetime(2026,10,20,22,tzinfo=timezone.utc)


def test_slot_validation_rejects_daily_and_wrong_cinematic_week():
    assert not is_weekly_slot(datetime(2026,10,22,7,tzinfo=KST))
    assert not is_weekly_slot(datetime(2026,10,21,19,tzinfo=KST))
    assert not is_weekly_slot(datetime(2026,10,21,7,tzinfo=KST),lane='cute_game')


def test_legacy_monday_publication_does_not_consume_first_new_wednesday():
    past=Playlist(id='old', title='Legacy daily', metadata_json={'youtube_channel_id':'A','youtube_public_at':'2026-10-18T22:00:00Z'})
    class DB:
        def scalars(self,*args): return SimpleNamespace(all=lambda:[past])
    services=SimpleNamespace(settings=SimpleNamespace(youtube_schedule_public_enabled=True,youtube_schedule_min_lead_minutes=30))
    assert next_youtube_scheduled_publish_at(DB(),services,youtube_channel_id='A',now=NOW) == datetime(2026,10,20,22,tzinfo=timezone.utc)


def test_channels_are_distributed_and_storylight_is_manual_only():
    from app.utils.youtube_schedule_policy import weekday_for_channel
    from app.workflows.openclaw_runtime import MANUAL_ONLY_CHANNEL_TITLES
    assert {name: weekday_for_channel(name) for name in (
        'HaruHaru', '불송', 'Solwave Radio', 'BibliaCanto',
        'Tokyo Daydream Radio', 'Soft Hour Radio', 'sundaze',
        'Cinematic Pulse', 'Club Bloom',
    )} == {
        'HaruHaru': 0, '불송': 0, 'Solwave Radio': 1, 'BibliaCanto': 1,
        'Tokyo Daydream Radio': 2, 'Soft Hour Radio': 3, 'sundaze': 4,
        'Cinematic Pulse': 5, 'Club Bloom': 6,
    }
    assert weekday_for_channel(None, 'UCUpTHfTl_tgHS1rFtSQU7CA') == 2
    assert weekday_for_channel(None, 'UCc79xOcZwpomZHTb8FaQ1UQ') == 6
    assert {'Storylight OST', 'MusicSun'} <= MANUAL_ONLY_CHANNEL_TITLES


def test_saturday_cinematic_parity_and_occupied_slots():
    assert next_weekly_slot(NOW, weekday=5, lane='orchestra') == datetime(2026, 10, 24, 7, tzinfo=KST)
    assert next_weekly_slot(NOW, weekday=5, lane='cute_game') == datetime(2026, 10, 31, 7, tzinfo=KST)
    assert next_weekly_slot(NOW, weekday=5, lane='orchestra', occupied_dates={datetime(2026,10,24).date()}) == datetime(2026,11,7,7,tzinfo=KST)
    assert not is_weekly_slot(datetime(2026,10,31,7,tzinfo=KST), weekday=5, lane='orchestra')


def test_channel_schedule_and_metadata_weekday():
    from app.workflows.playlist_automation import youtube_schedule_metadata
    class DB:
        def scalars(self,*args): return SimpleNamespace(all=lambda: [])
    settings = SimpleNamespace(youtube_schedule_public_enabled=True, youtube_schedule_min_lead_minutes=30, youtube_schedule_timezone='Asia/Seoul')
    services = SimpleNamespace(settings=settings)
    slot = next_youtube_scheduled_publish_at(DB(), services, youtube_channel_title='Soft Hour Radio', now=NOW)
    assert slot == datetime(2026,10,21,22,tzinfo=timezone.utc)
    assert youtube_schedule_metadata(services, slot)['youtube_schedule_weekday'] == 'Thursday'
