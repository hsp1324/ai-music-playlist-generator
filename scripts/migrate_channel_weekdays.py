"""Plan/apply a verified migration of future YouTube schedules; dry run by default.

Run only after the server scheduler is deployed.  --lane-map points to a JSON
object of Cinematic release IDs to "orchestra" or "cute_game". Entries whose
stored metadata is ambiguous must be reviewed before an apply.
"""
import argparse
import json
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import Settings
from app.services.youtube_service import YouTubeService
from app.utils.youtube_schedule_policy import CHANNEL_IDS, CHANNEL_WEEKDAYS, PUBLISH_TIMEZONE, next_weekly_slot, weekday_for_channel


def parse(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--lane-map', type=Path)
    parser.add_argument('--env-file', default='/etc/ai-music-playlist-generator.env')
    parser.add_argument('--journal-dir', required=True, type=Path)
    args = parser.parse_args()
    lane_map = json.loads(args.lane_map.read_text()) if args.lane_map else {}
    settings = Settings(_env_file=args.env_file)
    db = sqlite3.connect(settings.storage_root / 'app.db', timeout=30)
    db.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc)
    grouped = defaultdict(list)
    for row in db.execute('select id,title,youtube_video_id,metadata_json from playlists where youtube_video_id is not null'):
        meta = json.loads(row['metadata_json'] or '{}')
        value = meta.get('youtube_scheduled_publish_at')
        if not value:
            continue
        old = parse(value)
        if old <= now:
            continue
        channel_id = str(meta.get('youtube_channel_id') or '').strip()
        channel_key = CHANNEL_IDS.get(channel_id)
        if channel_id in {"UCSUuys2V4ISgg6nDue_XhXQ", "UCuZoNimj_UYzv5TmENsqTnQ"}:
            continue  # MusicSun and Storylight are manually managed.
        if channel_key not in CHANNEL_WEEKDAYS:
            raise RuntimeError(f'Unrecognized channel for {row["id"]}; refusing to change it')
        lane = None
        if channel_key == 'cinematic pulse':
            lane = lane_map.get(row['id'])
            if lane not in ('orchestra', 'cute_game'):
                raise RuntimeError(f'Review Cinematic lane and supply --lane-map for {row["id"]}: {row["title"]}')
        grouped[channel_id].append((old, row, meta, channel_key, lane))

    plan = []
    for channel_id, items in grouped.items():
        occupied = set()
        cutoff = now + timedelta(minutes=max(int(settings.youtube_schedule_min_lead_minutes), 0))
        previous_by_lane = defaultdict(lambda: cutoff)
        for old, row, meta, channel_key, lane in sorted(items, key=lambda x: (x[0], x[1]['id'])):
            local = old.astimezone(PUBLISH_TIMEZONE)
            week_start = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            earliest = previous_by_lane[lane] if lane else max(previous_by_lane[lane], week_start.astimezone(timezone.utc))
            slot = next_weekly_slot(earliest - timedelta(microseconds=1), lead_minutes=0, lane=lane,
                                    occupied_dates=occupied, weekday=weekday_for_channel(channel_key, channel_id))
            occupied.add(slot.date())
            previous_by_lane[lane] = slot.astimezone(timezone.utc) + timedelta(microseconds=1)
            plan.append({'release_id': row['id'], 'video_id': row['youtube_video_id'], 'channel_id': channel_id,
                         'channel': channel_key, 'title': row['title'], 'lane': lane,
                         'old': old.isoformat(), 'new': slot.astimezone(timezone.utc).isoformat()})

    args.journal_dir.mkdir(parents=True, exist_ok=True)
    (args.journal_dir / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.apply:
        return
    with sqlite3.connect(args.journal_dir / 'app-before.db') as backup:
        db.backup(backup)
    service = YouTubeService(settings)
    receipts = []
    clients = {}
    # Abort before changing any video if a reservation is stale or no longer private.
    for item in plan:
        if item['channel_id'] not in clients:
            clients[item['channel_id']] = service._build_youtube_client(service._load_credentials(youtube_channel_id=item['channel_id']))
        client = clients[item['channel_id']]
        found = client.videos().list(part='status', id=item['video_id']).execute().get('items') or []
        if not found:
            raise RuntimeError(f'YouTube video missing: {item["video_id"]}')
        status = found[0].get('status') or {}
        if status.get('privacyStatus') != 'private' or not status.get('publishAt') or parse(status['publishAt']) != parse(item['old']):
            raise RuntimeError(f'YouTube status no longer matches plan: {item["video_id"]}')
    for item in plan:
        client = clients[item['channel_id']]
        raw = db.execute('select metadata_json from playlists where id=?', (item['release_id'],)).fetchone()[0]
        meta = json.loads(raw or '{}')
        if parse(meta['youtube_scheduled_publish_at']) != parse(item['old']):
            raise RuntimeError(f'Database changed during migration: {item["release_id"]}')
        target = parse(item['new'])
        # Record intent before the external API call so interrupted runs can be reconciled.
        (args.journal_dir / 'in-flight.json').write_text(json.dumps(item, ensure_ascii=False, indent=2))
        if target != parse(item['old']):
            service.update_video_schedule(video_id=item['video_id'], scheduled_publish_at=target, youtube_channel_id=item['channel_id'])
        for attempt in range(6):
            status = client.videos().list(part='status', id=item['video_id']).execute()['items'][0]['status']
            if status.get('privacyStatus') == 'private' and status.get('publishAt') and parse(status['publishAt']) == target:
                break
            time.sleep(1)
        else:
            raise RuntimeError(f'YouTube update verification failed: {item["video_id"]}')
        local = target.astimezone(PUBLISH_TIMEZONE)
        meta.update({'youtube_schedule_previous_publish_at': item['old'], 'youtube_scheduled_publish_at': item['new'],
                     'youtube_schedule_local_time': local.isoformat(), 'youtube_schedule_timezone': 'Asia/Seoul',
                     'youtube_schedule_weekday': local.strftime('%A'), 'youtube_schedule_hour': 7,
                     'youtube_schedule_minute': 0, 'youtube_schedule_interval_days': 14 if item['lane'] else 7,
                     'youtube_schedule_label': 'cinematic_' + item['lane'] if item['lane'] else 'weekly_channel'})
        if item['lane']:
            meta['cinematic_pulse_lane'] = item['lane']
        if 'youtube_publish_at' in meta:
            meta['youtube_publish_at'] = item['new']
        response = dict(meta.get('youtube_response') or {})
        response['status'] = status
        response['scheduled_publish_at'] = item['new']
        meta['youtube_response'] = response
        with db:
            db.execute('update playlists set metadata_json=?, updated_at=? where id=?',
                       (json.dumps(meta, ensure_ascii=False), datetime.now(timezone.utc).replace(tzinfo=None).isoformat(' '), item['release_id']))
        receipts.append({**item, 'verified_status': status})
        (args.journal_dir / 'receipts.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2))
        (args.journal_dir / 'in-flight.json').unlink()
        print('VERIFIED', item['channel'], item['video_id'], item['new'], flush=True)


if __name__ == '__main__':
    main()
