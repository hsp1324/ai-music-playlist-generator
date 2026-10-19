from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.models.youtube_comment_request import YouTubeCommentRequest
from app.services.registry import ServiceRegistry
from app.utils.genre_tokens import cached_track_genre_tokens, extract_genre_tokens_from_values
from app.utils.lyric_subtitles import lyric_lines_from_text


CLUB_BLOOM_CHANNEL_TITLE = "Club Bloom"
QUEUED_STATUS = "queued"
CLAIMED_STATUS = "claimed"
PRODUCING_STATUS = "producing"
PUBLISH_QUEUED_STATUS = "publish_queued"
COMPLETED_STATUS = "completed"
DEFERRED_STATUS = "deferred"

REQUEST_MARKERS = (
    "만들어",
    "만들어줘",
    "만들어 주세요",
    "만들어주세요",
    "해주세요",
    "해 주세요",
    "듣고 싶",
    "부탁",
    "추천",
    "플레이리스트",
    "playlist",
    "please",
    "request",
    "make ",
    "create ",
    "can you",
    "could you",
    "would you",
    "i want",
    "suggest",
    "recommend",
)
URL_PATTERN = re.compile(r"(?:https?://|www\.|\b[a-z0-9-]+\.(?:com|net|org|io)\b)", re.IGNORECASE)
DURATION_PATTERN = re.compile(r"(?P<value>\d{1,3})\s*(?P<unit>시간|hour|hours|hr|hrs|분|minute|minutes|min|mins)", re.IGNORECASE)

GENRE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Melodic Techno", ("melodic techno", "멜로딕 테크노")),
    ("Progressive House", ("progressive house", "프로그레시브 하우스")),
    ("Melodic House", ("melodic house", "멜로딕 하우스")),
    ("Tropical House", ("tropical house", "트로피컬 하우스")),
    ("Electro House", ("electro house", "일렉트로 하우스")),
    ("Future House", ("future house", "퓨처 하우스")),
    ("Bass House", ("bass house", "베이스 하우스")),
    ("Tech House", ("tech house", "테크 하우스", "테크하우스")),
    ("Deep House", ("deep house", "딥 하우스", "딥하우스")),
    ("Afro House", ("afro house", "아프로 하우스", "아프로하우스")),
    ("Disco House", ("disco house", "디스코 하우스")),
    ("UK Garage", ("uk garage", "ukg", "유케이 개러지", "영국 개러지")),
    ("Drum and Bass", ("drum and bass", "drum & bass", "dnb", "드럼앤베이스", "드럼 앤 베이스")),
    ("Future Bass", ("future bass", "퓨처 베이스")),
    ("Psytrance", ("psytrance", "psy trance", "싸이트랜스", "사이 트랜스")),
    ("Hardstyle", ("hardstyle", "하드스타일")),
    ("Breakbeat", ("breakbeat", "브레이크비트")),
    ("Jersey Club", ("jersey club", "저지 클럽")),
    ("Dubstep", ("dubstep", "덥스텝")),
    ("Techno", ("techno", "테크노")),
    ("Trance", ("trance", "트랜스")),
    ("House", ("house", "하우스")),
    ("EDM", ("edm", "이디엠")),
    ("Club Trap", ("club trap", "trap edm", "클럽 트랩")),
    ("Phonk", ("phonk", "폰크")),
)

MOOD_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dark", ("dark", "어두운", "다크")),
    ("energetic", ("energetic", "energy", "신나는", "에너지", "강렬한")),
    ("uplifting", ("uplifting", "희망찬", "기분 좋은")),
    ("dreamy", ("dreamy", "몽환", "몽환적인")),
    ("aggressive", ("aggressive", "공격적인", "하드한")),
    ("chill", ("chill", "칠한", "편안한")),
    ("night drive", ("night drive", "night-drive", "야간 드라이브", "밤 드라이브")),
    ("workout", ("workout", "gym", "운동", "헬스")),
    ("festival", ("festival", "페스티벌")),
)


class YouTubeCommentRequestError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_display_name(value: Any) -> str | None:
    cleaned = unicodedata.normalize("NFKC", str(value or "").strip())
    if URL_PATTERN.search(cleaned):
        return None
    cleaned = "".join(
        character
        for character in cleaned
        if (
            unicodedata.category(character)[0] in {"L", "M", "N"}
            or character in {" ", "@", "_", ".", "-"}
        )
    )
    cleaned = " ".join(cleaned.split()).strip(" .-_")
    return cleaned[:80] if cleaned and cleaned != "@" else None


def _extract_duration_seconds(
    text: str,
    default_seconds: int,
    *,
    min_seconds: int,
    max_seconds: int,
) -> int:
    lower_bound = max(int(min_seconds or 0), 600)
    upper_bound = max(int(max_seconds or 0), lower_bound)
    match = DURATION_PATTERN.search(text)
    if not match:
        return min(max(int(default_seconds or 3600), lower_bound), upper_bound)
    value = int(match.group("value"))
    unit = match.group("unit").lower()
    seconds = value * 3600 if unit in {"시간", "hour", "hours", "hr", "hrs"} else value * 60
    return min(max(seconds, lower_bound), upper_bound)


def normalize_club_bloom_comment_request(
    text: str,
    *,
    default_duration_seconds: int = 3600,
    min_duration_seconds: int = 1800,
    max_duration_seconds: int = 7200,
) -> dict[str, Any] | None:
    source_text = " ".join(str(text or "").strip().split())
    lowered = source_text.lower()
    if not source_text or len(source_text) > 600 or URL_PATTERN.search(source_text):
        return None
    if not any(marker in lowered for marker in REQUEST_MARKERS):
        return None

    genres: list[str] = []
    matched_aliases: list[str] = []
    for canonical, aliases in GENRE_ALIASES:
        matched = next((alias for alias in aliases if alias in lowered), None)
        if not matched:
            continue
        if any(matched in existing or existing in matched for existing in matched_aliases):
            continue
        genres.append(canonical)
        matched_aliases.append(matched)
    if not genres:
        return None

    moods = [canonical for canonical, aliases in MOOD_ALIASES if any(alias in lowered for alias in aliases)]
    requested_mood = ", ".join(dict.fromkeys(moods)) or None
    duration_seconds = _extract_duration_seconds(
        lowered,
        default_duration_seconds,
        min_seconds=min_duration_seconds,
        max_seconds=max_duration_seconds,
    )
    genre_text = " + ".join(genres)
    mood_text = f" Mood: {requested_mood}." if requested_mood else ""
    normalized_prompt = (
        f"Create an instrumental Club Bloom playlist in {genre_text}."
        f"{mood_text} Target duration: {duration_seconds // 60} minutes. No vocals."
    )
    request_summary = f"{genre_text} | {requested_mood or 'instrumental'} | {duration_seconds // 60} min"
    return {
        "requested_genres": genres,
        "requested_mood": requested_mood,
        "requested_duration_seconds": duration_seconds,
        "request_summary": request_summary,
        "normalized_prompt": normalized_prompt,
        "source_text": source_text,
    }


def serialize_comment_request(item: YouTubeCommentRequest) -> dict[str, Any]:
    return {
        "id": item.id,
        "channel_title": item.channel_title,
        "source_video_id": item.source_video_id,
        "comment_id": item.comment_id,
        "requester_display_name": item.requester_display_name,
        "requester_channel_id": item.requester_channel_id,
        "requested_genres": list(item.requested_genres_json or []),
        "requested_mood": item.requested_mood,
        "requested_duration_seconds": item.requested_duration_seconds,
        "request_summary": item.request_summary,
        "queue_rank": item.queue_rank,
        "status": item.status,
        "release_id": item.release_id,
        "claim_owner": item.claim_owner,
        "claim_run_id": item.claim_run_id,
        "claim_expires_at": item.claim_expires_at.isoformat() if item.claim_expires_at else None,
        "available_after": item.available_after.isoformat() if item.available_after else None,
        "defer_count": item.defer_count,
        "defer_reason": item.defer_reason,
        "scheduled_publish_at": item.scheduled_publish_at.isoformat() if item.scheduled_publish_at else None,
        "schedule_plan_status": item.schedule_plan_status,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def sync_club_bloom_comment_requests(db: Session, services: ServiceRegistry) -> dict[str, Any]:
    settings = services.settings
    channel_title = str(settings.youtube_comment_request_channel_title or CLUB_BLOOM_CHANNEL_TITLE).strip()
    if not settings.youtube_comment_requests_enabled:
        return {"enabled": False, "channel_title": channel_title, "scanned": 0, "created": 0}
    if channel_title != CLUB_BLOOM_CHANNEL_TITLE:
        raise YouTubeCommentRequestError(
            "The YouTube comment request pilot is restricted to Club Bloom.",
            code="unsupported_channel",
        )
    allowed_channels = {
        item.strip()
        for item in str(getattr(settings, "youtube_comment_request_channels", "") or "").split(",")
        if item.strip()
    }
    if allowed_channels != {CLUB_BLOOM_CHANNEL_TITLE}:
        raise YouTubeCommentRequestError(
            "The YouTube comment request pilot allowlist must contain Club Bloom only.",
            code="unsupported_channel",
        )
    channel = services.youtube.get_channel_by_title(channel_title)
    if not channel:
        raise YouTubeCommentRequestError(
            "Club Bloom is not connected to the app YouTube registry.",
            code="channel_not_connected",
        )
    channel_id = str(channel.get("id") or "").strip()
    comments = services.youtube.list_channel_comments(
        channel_id=channel_id,
        max_results=settings.youtube_comment_request_poll_max_results,
    )
    comment_ids = [str(item.get("comment_id") or "").strip() for item in comments]
    existing_ids = set(
        db.scalars(
            select(YouTubeCommentRequest.comment_id).where(YouTubeCommentRequest.comment_id.in_(comment_ids))
        ).all()
    ) if comment_ids else set()

    created = 0
    ignored = 0
    next_queue_rank = int(
        db.scalar(
            select(func.max(YouTubeCommentRequest.queue_rank)).where(
                YouTubeCommentRequest.youtube_channel_id == channel_id
            )
        )
        or 0
    )
    ordered_comments = sorted(
        comments,
        key=lambda item: (
            _parse_datetime(item.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
            str(item.get("comment_id") or ""),
        ),
    )
    for comment in ordered_comments:
        comment_id = str(comment.get("comment_id") or "").strip()
        requester_channel_id = str(comment.get("requester_channel_id") or "").strip()
        if not comment_id or comment_id in existing_ids or requester_channel_id == channel_id:
            continue
        normalized = normalize_club_bloom_comment_request(
            str(comment.get("text") or ""),
            default_duration_seconds=settings.youtube_comment_request_default_duration_seconds,
            min_duration_seconds=settings.youtube_comment_request_min_duration_seconds,
            max_duration_seconds=settings.youtube_comment_request_max_duration_seconds,
        )
        if not normalized:
            ignored += 1
            continue
        next_queue_rank += 1
        db.add(
            YouTubeCommentRequest(
                channel_title=CLUB_BLOOM_CHANNEL_TITLE,
                youtube_channel_id=channel_id,
                source_video_id=str(comment.get("source_video_id") or "").strip(),
                comment_id=comment_id,
                requester_display_name=_safe_display_name(comment.get("requester_display_name")),
                requester_channel_id=requester_channel_id or None,
                requested_genres_json=normalized["requested_genres"],
                requested_mood=normalized["requested_mood"],
                requested_duration_seconds=normalized["requested_duration_seconds"],
                request_summary=normalized["request_summary"],
                normalized_prompt=normalized["normalized_prompt"],
                source_text=normalized["source_text"],
                queue_rank=next_queue_rank,
                source_published_at=_parse_datetime(comment.get("published_at")),
            )
        )
        existing_ids.add(comment_id)
        created += 1
    if created:
        db.commit()
    return {
        "enabled": True,
        "channel_title": channel_title,
        "youtube_channel_id": channel_id,
        "scanned": len(comments),
        "created": created,
        "ignored": ignored,
    }


def list_comment_requests(
    db: Session,
    *,
    channel_title: str = CLUB_BLOOM_CHANNEL_TITLE,
    status: str = QUEUED_STATUS,
    limit: int = 20,
) -> list[YouTubeCommentRequest]:
    if channel_title != CLUB_BLOOM_CHANNEL_TITLE:
        raise YouTubeCommentRequestError(
            "The YouTube comment request pilot is restricted to Club Bloom.",
            code="unsupported_channel",
        )
    now = _utcnow()
    if status == QUEUED_STATUS:
        expired = db.execute(
            update(YouTubeCommentRequest)
            .where(
                YouTubeCommentRequest.channel_title == CLUB_BLOOM_CHANNEL_TITLE,
                YouTubeCommentRequest.status.in_([CLAIMED_STATUS, PRODUCING_STATUS]),
                YouTubeCommentRequest.claim_expires_at <= now,
            )
            .values(
                status=QUEUED_STATUS,
                claim_owner=None,
                claim_run_id=None,
                claimed_at=None,
                claim_expires_at=None,
                updated_at=now,
            )
        )
        if expired.rowcount:
            db.commit()
    statement = (
        select(YouTubeCommentRequest)
        .where(
            YouTubeCommentRequest.channel_title == CLUB_BLOOM_CHANNEL_TITLE,
            YouTubeCommentRequest.status == status,
        )
        .order_by(YouTubeCommentRequest.queue_rank.asc(), YouTubeCommentRequest.id.asc())
        .limit(max(1, min(int(limit or 20), 100)))
    )
    if status == QUEUED_STATUS:
        statement = statement.where(
            or_(
                YouTubeCommentRequest.available_after.is_(None),
                YouTubeCommentRequest.available_after <= now,
            )
        )
    return list(db.scalars(statement).all())


def claim_comment_request(
    db: Session,
    *,
    request_id: str,
    owner: str,
    run_id: str,
    lease_seconds: int = 7200,
) -> YouTubeCommentRequest:
    normalized_owner = str(owner or "openclaw").strip() or "openclaw"
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        raise YouTubeCommentRequestError("run_id is required to claim a comment request.", code="run_id_required")
    now = _utcnow()
    existing = db.get(YouTubeCommentRequest, request_id)
    if not existing:
        raise YouTubeCommentRequestError("Comment request not found.", code="request_not_found")
    if existing.status in {CLAIMED_STATUS, PRODUCING_STATUS} and existing.claim_run_id == normalized_run_id:
        existing.claim_expires_at = now + timedelta(seconds=max(int(lease_seconds or 0), 60))
        existing.updated_at = now
        db.add(existing)
        db.commit()
        return existing

    eligible_status = existing.status == QUEUED_STATUS or (
        existing.status in {CLAIMED_STATUS, PRODUCING_STATUS}
        and existing.claim_expires_at is not None
        and _parse_datetime(existing.claim_expires_at) <= now
    )
    if not eligible_status:
        raise YouTubeCommentRequestError(
            "The comment request is no longer available for claim.",
            code="request_not_claimable",
        )
    oldest = db.scalar(
        select(YouTubeCommentRequest)
        .where(
            YouTubeCommentRequest.channel_title == CLUB_BLOOM_CHANNEL_TITLE,
            or_(
                YouTubeCommentRequest.status == QUEUED_STATUS,
                (
                    YouTubeCommentRequest.status.in_([CLAIMED_STATUS, PRODUCING_STATUS])
                    & (YouTubeCommentRequest.claim_expires_at <= now)
                ),
            ),
        )
        .order_by(YouTubeCommentRequest.queue_rank.asc(), YouTubeCommentRequest.id.asc())
        .limit(1)
    )
    if oldest is None or oldest.id != request_id:
        raise YouTubeCommentRequestError(
            "Claim the oldest eligible Club Bloom request first.",
            code="request_not_fifo",
        )
    claim_expires_at = now + timedelta(seconds=max(int(lease_seconds or 0), 60))
    result = db.execute(
        update(YouTubeCommentRequest)
        .where(
            YouTubeCommentRequest.id == request_id,
            YouTubeCommentRequest.channel_title == CLUB_BLOOM_CHANNEL_TITLE,
            or_(
                YouTubeCommentRequest.status == QUEUED_STATUS,
                (
                    YouTubeCommentRequest.status.in_([CLAIMED_STATUS, PRODUCING_STATUS])
                    & (YouTubeCommentRequest.claim_expires_at <= now)
                ),
            ),
        )
        .values(
            status=CLAIMED_STATUS,
            claim_owner=normalized_owner,
            claim_run_id=normalized_run_id,
            claimed_at=now,
            claim_expires_at=claim_expires_at,
            updated_at=now,
        )
    )
    if result.rowcount:
        db.commit()
        return db.get(YouTubeCommentRequest, request_id)

    db.rollback()
    existing = db.get(YouTubeCommentRequest, request_id)
    if existing and existing.status == CLAIMED_STATUS and existing.claim_run_id == normalized_run_id:
        return existing
    raise YouTubeCommentRequestError(
        "The comment request is no longer available for claim.",
        code="request_not_claimable",
    )


def _request_attribution(item: YouTubeCommentRequest) -> str:
    if item.requester_display_name:
        return f"Created in response to {item.requester_display_name}'s playlist request."
    return "Created in response to a listener's playlist request."


def _manual_reused_track_ids(meta: dict[str, Any]) -> set[str]:
    return {
        str(entry.get("track_id") or "").strip()
        for entry in meta.get("assignment_history") or []
        if isinstance(entry, dict)
        and "reuse" in str(entry.get("actor") or "").lower()
        and str(entry.get("track_id") or "").strip()
    }


def _validate_release_request_mix(
    db: Session,
    *,
    request: YouTubeCommentRequest,
    release: Playlist,
    meta: dict[str, Any],
) -> bool:
    items = list(
        db.scalars(
            select(PlaylistItem).where(PlaylistItem.playlist_id == release.id)
        ).all()
    )
    if not items:
        return False
    reused_ids = {
        str(track_id).strip()
        for track_id in meta.get("auto_reused_track_ids") or []
        if str(track_id).strip()
    }
    reused_ids.update(_manual_reused_track_ids(meta))
    total_seconds = sum(max(int(item.included_duration_seconds or 0), 0) for item in items)
    minimum_duration = max(int(request.requested_duration_seconds or 0) - 300, 600)
    if total_seconds < minimum_duration:
        raise YouTubeCommentRequestError(
            "The Club Bloom request release has not reached its requested duration.",
            code="request_mix_policy_failed",
        )
    reused_seconds = sum(
        max(int(item.included_duration_seconds or 0), 0)
        for item in items
        if item.track_id in reused_ids
    )
    new_seconds = max(total_seconds - reused_seconds, 0)
    if reused_seconds and total_seconds:
        new_ratio = new_seconds / total_seconds
        if new_ratio < 0.40 or new_ratio > 0.80:
            raise YouTubeCommentRequestError(
                "A Club Bloom request mix with catalog reuse must contain 40-80% new audio.",
                code="request_mix_policy_failed",
            )
    last_reuse_attempt = meta.get("auto_reuse_last_attempt")
    compatible_count = (
        int(last_reuse_attempt.get("candidate_count") or 0)
        if isinstance(last_reuse_attempt, dict)
        else 0
    )
    if compatible_count > 0 and not reused_ids:
        raise YouTubeCommentRequestError(
            "At least one compatible Club Bloom catalog track must be reused.",
            code="request_mix_policy_failed",
        )
    if not reused_ids:
        return True

    requested_tokens = set(extract_genre_tokens_from_values(list(request.requested_genres_json or [])))
    for track_id in reused_ids:
        track = db.get(Track, track_id)
        if (
            not track
            or track.status != TrackStatus.approved
            or not track.audio_path
            or track.audio_path.startswith(("http://", "https://"))
        ):
            raise YouTubeCommentRequestError(
                "A reused request track is unapproved or missing local audio.",
                code="request_mix_policy_failed",
            )
        if not Path(track.audio_path).exists() or lyric_lines_from_text(track.lyrics):
            raise YouTubeCommentRequestError(
                "Reused Club Bloom request tracks must be local and instrumental.",
                code="request_mix_policy_failed",
            )
        track_meta = dict(track.metadata_json or {})
        if any(
            track_meta.get(key)
            for key in ("reuse_disabled", "copyright_blocked", "blocked_from_reuse")
        ) or str(track_meta.get("user_rating") or "").strip().lower() == "dislike":
            raise YouTubeCommentRequestError(
                "A reused request track is blocked by catalog policy.",
                code="request_mix_policy_failed",
            )
        if requested_tokens and not (requested_tokens & set(cached_track_genre_tokens(track))):
            raise YouTubeCommentRequestError(
                "A reused request track does not match the requested genre lane.",
                code="request_mix_policy_failed",
            )
        source_playlists = db.scalars(
            select(Playlist)
            .join(PlaylistItem, PlaylistItem.playlist_id == Playlist.id)
            .where(
                PlaylistItem.track_id == track_id,
                Playlist.id != release.id,
                Playlist.youtube_video_id.is_not(None),
            )
        ).all()
        if not any(
            _playlist_is_club_bloom(source, request.youtube_channel_id)
            for source in source_playlists
        ):
            raise YouTubeCommentRequestError(
                "A reused request track is not owned by a published Club Bloom release.",
                code="request_mix_policy_failed",
            )
    return True


def complete_comment_request(
    db: Session,
    *,
    request_id: str,
    release_id: str,
    provenance: dict[str, Any] | None = None,
    scheduled_publish_at: datetime | None = None,
    idempotency_key: str = "",
) -> YouTubeCommentRequest:
    item = db.get(YouTubeCommentRequest, request_id)
    if not item:
        raise YouTubeCommentRequestError("Comment request not found.", code="request_not_found")
    release = db.get(Playlist, str(release_id or "").strip())
    if not release:
        raise YouTubeCommentRequestError("Release not found.", code="release_not_found")
    normalized_key = str(idempotency_key or "").strip()[:255]
    if item.release_id == release.id and item.status in {PUBLISH_QUEUED_STATUS, COMPLETED_STATUS}:
        return item
    if item.status not in {CLAIMED_STATUS, PRODUCING_STATUS}:
        raise YouTubeCommentRequestError("Claim the comment request before completing it.", code="request_not_claimed")
    if scheduled_publish_at and item.schedule_plan_status != "applied":
        raise YouTubeCommentRequestError(
            "Use prioritize-request so the app owns every Club Bloom schedule change.",
            code="schedule_plan_required",
        )
    other_request = db.scalar(
        select(YouTubeCommentRequest.id).where(
            YouTubeCommentRequest.release_id == release.id,
            YouTubeCommentRequest.id != item.id,
        )
    )
    if other_request:
        raise YouTubeCommentRequestError(
            "The release is already linked to another comment request.",
            code="release_already_linked",
        )
    other_release = db.scalar(
        select(Playlist.id).where(
            Playlist.youtube_comment_request_id == item.id,
            Playlist.id != release.id,
        )
    )
    if other_release:
        raise YouTubeCommentRequestError(
            "The comment request is already linked to another release.",
            code="release_already_linked",
        )

    meta = dict(release.metadata_json or {})
    existing_target = str(
        meta.get("youtube_channel_title") or meta.get("target_youtube_channel_title") or ""
    ).strip()
    if existing_target and existing_target != CLUB_BLOOM_CHANNEL_TITLE:
        raise YouTubeCommentRequestError(
            "A Club Bloom comment request cannot be attached to another channel.",
            code="release_channel_mismatch",
        )
    release_has_tracks = _validate_release_request_mix(db, request=item, release=release, meta=meta)
    if scheduled_publish_at and not release_has_tracks:
        raise YouTubeCommentRequestError(
            "An asset-free request release cannot be marked as scheduled.",
            code="release_not_publish_ready",
        )
    attribution = _request_attribution(item)
    request_meta = {
        "id": item.id,
        "source_video_id": item.source_video_id,
        "comment_id": item.comment_id,
        "requester_display_name": item.requester_display_name,
        "requested_genres": list(item.requested_genres_json or []),
        "requested_mood": item.requested_mood,
        "requested_duration_seconds": item.requested_duration_seconds,
        "normalized_prompt": item.normalized_prompt,
        "request_summary": item.request_summary,
        "queue_rank": item.queue_rank,
        "attribution": attribution,
    }
    meta["target_youtube_channel_title"] = CLUB_BLOOM_CHANNEL_TITLE
    meta["youtube_comment_request_id"] = item.id
    meta["youtube_comment_request"] = request_meta
    meta["youtube_comment_request_lane"] = True
    meta["youtube_comment_request_attribution"] = attribution
    meta["youtube_comment_request_attribution_ko"] = (
        f"{item.requester_display_name}님의 요청으로 제작된 플레이리스트입니다."
        if item.requester_display_name
        else "한 청취자의 요청으로 제작된 플레이리스트입니다."
    )
    description = str(meta.get("youtube_description") or "").strip()
    if description and not description.startswith(attribution):
        meta["youtube_description"] = f"{attribution}\n\n{description}"
    release.metadata_json = meta
    release.youtube_comment_request_id = item.id

    now = _utcnow()
    if not release_has_tracks:
        item.status = PRODUCING_STATUS
    else:
        item.status = PUBLISH_QUEUED_STATUS
    item.release_id = release.id
    item.provenance_json = dict(provenance or {})
    item.completion_idempotency_key = normalized_key or item.completion_idempotency_key
    item.scheduled_publish_at = scheduled_publish_at
    item.completed_at = None
    if release_has_tracks:
        item.claim_expires_at = None
    operation_results = dict(item.operation_results_json or {})
    operation_results["complete"] = {
        "idempotency_key": normalized_key or None,
        "release_id": release.id,
        "status": item.status,
        "recorded_at": now.isoformat(),
    }
    item.operation_results_json = operation_results
    item.updated_at = now
    db.add(release)
    db.add(item)
    db.commit()
    return item


def defer_comment_request(
    db: Session,
    *,
    request_id: str,
    reason: str,
    idempotency_key: str = "",
    release_id: str = "",
) -> YouTubeCommentRequest:
    item = db.get(YouTubeCommentRequest, request_id)
    if not item:
        raise YouTubeCommentRequestError("Comment request not found.", code="request_not_found")
    normalized_key = str(idempotency_key or "").strip()[:255]
    if item.status == DEFERRED_STATUS and (
        not normalized_key or item.defer_idempotency_key == normalized_key
    ):
        return item
    if item.status == COMPLETED_STATUS:
        raise YouTubeCommentRequestError("Completed requests cannot be deferred.", code="request_completed")
    now = _utcnow()
    linked_release_id = str(release_id or item.release_id or "").strip()
    if linked_release_id:
        release = db.get(Playlist, linked_release_id)
        if not release:
            raise YouTubeCommentRequestError("Release not found.", code="release_not_found")
        meta = dict(release.metadata_json or {})
        target_channel = str(
            meta.get("target_youtube_channel_title") or meta.get("youtube_channel_title") or ""
        ).strip()
        if target_channel and target_channel != CLUB_BLOOM_CHANNEL_TITLE:
            raise YouTubeCommentRequestError(
                "A Club Bloom request cannot resume in another channel's release.",
                code="release_channel_mismatch",
            )
        if release.youtube_comment_request_id not in {None, item.id}:
            raise YouTubeCommentRequestError(
                "The release is already linked to another comment request.",
                code="release_already_linked",
            )
        other_release = db.scalar(
            select(Playlist.id).where(
                Playlist.youtube_comment_request_id == item.id,
                Playlist.id != release.id,
            )
        )
        if other_release:
            raise YouTubeCommentRequestError(
                "The comment request is already linked to another release.",
                code="release_already_linked",
            )
        release.youtube_comment_request_id = item.id
        db.add(release)
        db.flush()
        item.release_id = release.id
        has_assets = bool(
            release.items
            or release.output_audio_path
            or release.output_video_path
            or any(
                meta.get(key)
                for key in (
                    "cover_path",
                    "cover_image_path",
                    "thumbnail_path",
                    "youtube_thumbnail_path",
                    "loop_video_path",
                )
            )
        )
        if not has_assets:
            from app.workflows.playlist_automation import set_playlist_workspace_archive_state

            set_playlist_workspace_archive_state(
                db,
                playlist_id=release.id,
                actor="openclaw:youtube-comment-request-defer",
                archived=True,
                revive_rejected=False,
            )

    item.status = DEFERRED_STATUS
    item.claim_owner = None
    item.claim_run_id = None
    item.claimed_at = None
    item.claim_expires_at = None
    item.defer_count = int(item.defer_count or 0) + 1
    item.deferred_at = now
    item.defer_reason = " ".join(str(reason or "recoverable failure").strip().split())[:1000]
    item.available_after = None
    item.defer_idempotency_key = normalized_key or item.defer_idempotency_key
    operation_results = dict(item.operation_results_json or {})
    operation_results["defer"] = {
        "idempotency_key": normalized_key or None,
        "release_id": item.release_id,
        "status": DEFERRED_STATUS,
        "recorded_at": now.isoformat(),
    }
    item.operation_results_json = operation_results
    item.updated_at = now
    db.add(item)
    db.commit()
    return item


def requeue_comment_request(db: Session, *, request_id: str) -> YouTubeCommentRequest:
    item = db.get(YouTubeCommentRequest, request_id)
    if not item:
        raise YouTubeCommentRequestError("Comment request not found.", code="request_not_found")
    if item.status != DEFERRED_STATUS:
        raise YouTubeCommentRequestError("Only deferred requests can be requeued.", code="request_not_deferred")
    next_rank = int(
        db.scalar(
            select(func.max(YouTubeCommentRequest.queue_rank)).where(
                YouTubeCommentRequest.youtube_channel_id == item.youtube_channel_id
            )
        )
        or 0
    ) + 1
    now = _utcnow()
    item.queue_rank = next_rank
    item.status = QUEUED_STATUS
    item.defer_reason = None
    item.available_after = None
    item.updated_at = now
    db.add(item)
    db.commit()
    return item


def _future_schedule(meta: dict[str, Any], *, now: datetime) -> datetime | None:
    values: list[datetime] = []
    for value in (meta.get("youtube_scheduled_publish_at"), meta.get("youtube_publish_at")):
        parsed = _parse_datetime(value)
        if parsed and parsed > now:
            values.append(parsed)
    response = meta.get("youtube_response") if isinstance(meta.get("youtube_response"), dict) else {}
    status = response.get("status") if isinstance(response.get("status"), dict) else {}
    parsed = _parse_datetime(status.get("publishAt"))
    if parsed and parsed > now:
        values.append(parsed)
    return max(values) if values else None


def _playlist_is_club_bloom(playlist: Playlist, youtube_channel_id: str) -> bool:
    meta = dict(playlist.metadata_json or {})
    stored_channel_id = str(meta.get("youtube_channel_id") or "").strip()
    if youtube_channel_id and stored_channel_id:
        return stored_channel_id == youtube_channel_id
    titles = {
        str(meta.get("youtube_channel_title") or "").strip(),
        str(meta.get("target_youtube_channel_title") or "").strip(),
    }
    return CLUB_BLOOM_CHANNEL_TITLE in titles


def _schedule_is_locked(meta: dict[str, Any]) -> bool:
    return any(
        bool(meta.get(key))
        for key in (
            "youtube_schedule_locked",
            "youtube_schedule_manual_lock",
            "youtube_scheduling_lock",
            "youtube_schedule_fixed",
        )
    )


def _playlist_is_public(meta: dict[str, Any]) -> bool:
    response = meta.get("youtube_response") if isinstance(meta.get("youtube_response"), dict) else {}
    status = response.get("status") if isinstance(response.get("status"), dict) else {}
    privacy = str(
        status.get("privacyStatus")
        or meta.get("youtube_privacy_status")
        or meta.get("privacy_status")
        or ""
    ).strip().lower()
    return privacy in {"public", "unlisted"}


def _set_schedule_metadata(meta: dict[str, Any], scheduled_at: datetime, *, request_lane: bool) -> dict[str, Any]:
    scheduled_utc = scheduled_at.astimezone(timezone.utc).replace(microsecond=0)
    value = scheduled_utc.isoformat()
    meta["youtube_scheduled_publish_at"] = value
    meta["youtube_schedule_source"] = "youtube_comment_request_priority"
    if request_lane:
        meta["youtube_comment_request_lane"] = True
    response = dict(meta.get("youtube_response") or {}) if isinstance(meta.get("youtube_response"), dict) else {}
    status = dict(response.get("status") or {}) if isinstance(response.get("status"), dict) else {}
    if status:
        status["privacyStatus"] = "private"
        status["publishAt"] = value.replace("+00:00", "Z")
        response["status"] = status
        meta["youtube_response"] = response
    return meta


def _schedule_plan_result(request: YouTubeCommentRequest) -> dict[str, Any]:
    plan = dict(request.schedule_plan_json or {})
    return {
        "request_id": request.id,
        "release_id": request.release_id,
        "schedule_plan_key": request.schedule_plan_key,
        "schedule_plan_status": request.schedule_plan_status,
        "scheduled_publish_at": (
            request.scheduled_publish_at.isoformat() if request.scheduled_publish_at else None
        ),
        "changes": list(plan.get("changes") or []),
        "skipped": list(plan.get("skipped") or []),
        "error": plan.get("error"),
    }


def _next_open_date(candidate: datetime, occupied_dates: set) -> datetime:
    from app.utils.youtube_schedule_policy import next_weekly_slot
    slot = next_weekly_slot(candidate - timedelta(seconds=1), lead_minutes=0).astimezone(timezone.utc)
    while slot.date() in occupied_dates:
        slot += timedelta(days=7)
    return slot


def _persist_schedule_plan(
    db: Session,
    request: YouTubeCommentRequest,
    *,
    target: Playlist,
    channel_id: str,
    idempotency_key: str,
    now: datetime,
    active_playlist_ids: set[str],
    services: ServiceRegistry,
) -> None:
    earlier_request = db.scalar(
        select(YouTubeCommentRequest)
        .where(
            YouTubeCommentRequest.youtube_channel_id == request.youtube_channel_id,
            YouTubeCommentRequest.queue_rank < request.queue_rank,
            YouTubeCommentRequest.status.notin_([DEFERRED_STATUS, "ignored", "withdrawn"]),
            YouTubeCommentRequest.scheduled_publish_at.is_(None),
        )
        .order_by(YouTubeCommentRequest.queue_rank.asc())
        .limit(1)
    )
    if earlier_request:
        raise YouTubeCommentRequestError(
            "An earlier Club Bloom request must reserve its publish slot first.",
            code="earlier_request_pending",
        )

    request_lane: list[tuple[Playlist, datetime]] = []
    normal_lane: list[tuple[Playlist, datetime]] = []
    fixed_lane: list[tuple[Playlist, datetime, str]] = []
    for playlist in db.scalars(select(Playlist).where(Playlist.id != target.id)).all():
        if not _playlist_is_club_bloom(playlist, channel_id):
            continue
        meta = dict(playlist.metadata_json or {})
        scheduled_at = _future_schedule(meta, now=now)
        if not scheduled_at:
            continue
        fixed_reason = ""
        if _playlist_is_public(meta):
            fixed_reason = "already_public"
        elif _schedule_is_locked(meta):
            fixed_reason = "schedule_locked"
        elif playlist.id in active_playlist_ids:
            fixed_reason = "active_render_or_upload"
        if fixed_reason:
            fixed_lane.append((playlist, scheduled_at, fixed_reason))
        elif meta.get("youtube_comment_request_lane"):
            request_lane.append((playlist, scheduled_at))
        else:
            normal_lane.append((playlist, scheduled_at))

    request_lane.sort(key=lambda item: item[1])
    normal_lane.sort(key=lambda item: item[1])
    occupied_dates = {scheduled_at.date() for _, scheduled_at, _ in fixed_lane}
    occupied_dates.update(scheduled_at.date() for _, scheduled_at in request_lane)

    if request_lane:
        base_time = normal_lane[0][1] if normal_lane else request_lane[-1][1]
        target_schedule = request_lane[-1][1] + timedelta(days=7)
        target_schedule = target_schedule.replace(
            hour=base_time.hour,
            minute=base_time.minute,
            second=base_time.second,
            microsecond=0,
        )
    elif normal_lane:
        target_schedule = normal_lane[0][1]
    else:
        from app.workflows.playlist_automation import next_youtube_scheduled_publish_at

        target_schedule = next_youtube_scheduled_publish_at(
            db,
            services,
            youtube_channel_id=channel_id,
            youtube_channel_title=CLUB_BLOOM_CHANNEL_TITLE,
            now=now,
        )
    if target_schedule is None:
        raise YouTubeCommentRequestError("YouTube public scheduling is disabled.", code="scheduling_disabled")
    target_schedule = _next_open_date(target_schedule, occupied_dates)
    occupied_dates.add(target_schedule.date())

    planned_changes: list[dict[str, Any]] = [
        {
            "release_id": target.id,
            "youtube_video_id": target.youtube_video_id,
            "old_scheduled_publish_at": (
                current.isoformat()
                if (current := _future_schedule(dict(target.metadata_json or {}), now=now))
                else None
            ),
            "new_scheduled_publish_at": target_schedule.isoformat(),
            "request_lane": True,
            "state": "planned",
        }
    ]
    previous_schedule = target_schedule
    for playlist, old_schedule in normal_lane:
        desired = old_schedule + timedelta(days=7)
        if desired.date() <= previous_schedule.date():
            desired = previous_schedule + timedelta(days=7)
            desired = desired.replace(
                hour=old_schedule.hour,
                minute=old_schedule.minute,
                second=old_schedule.second,
                microsecond=0,
            )
        desired = _next_open_date(desired, occupied_dates)
        occupied_dates.add(desired.date())
        previous_schedule = desired
        planned_changes.append(
            {
                "release_id": playlist.id,
                "youtube_video_id": playlist.youtube_video_id,
                "old_scheduled_publish_at": old_schedule.isoformat(),
                "new_scheduled_publish_at": desired.isoformat(),
                "request_lane": False,
                "state": "planned",
            }
        )

    plan_key = idempotency_key or f"youtube-comment-request:{request.id}:{target.id}"
    request.schedule_plan_key = plan_key[:255]
    request.schedule_plan_status = "planned"
    request.schedule_plan_json = {
        "version": 1,
        "request_id": request.id,
        "release_id": target.id,
        "channel_id": channel_id,
        "created_at": now.isoformat(),
        "changes": planned_changes,
        "skipped": [
            {
                "release_id": playlist.id,
                "youtube_video_id": playlist.youtube_video_id,
                "scheduled_publish_at": scheduled_at.isoformat(),
                "reason": reason,
            }
            for playlist, scheduled_at, reason in fixed_lane
        ],
    }
    request.updated_at = now
    db.add(request)
    db.commit()


def _apply_schedule_plan(
    db: Session,
    services: ServiceRegistry,
    request: YouTubeCommentRequest,
) -> dict[str, Any]:
    plan = dict(request.schedule_plan_json or {})
    changes = [dict(change) for change in plan.get("changes") or []]
    channel_id = str(plan.get("channel_id") or request.youtube_channel_id or "").strip()
    for index, change in enumerate(changes):
        if change.get("state") == "applied":
            continue
        playlist = db.get(Playlist, str(change.get("release_id") or ""))
        if not playlist or not _playlist_is_club_bloom(playlist, channel_id):
            error = "A planned Club Bloom release is missing or changed channels."
            change["state"] = "failed"
            change["error"] = error
        else:
            try:
                new_schedule = _parse_datetime(change.get("new_scheduled_publish_at"))
                if new_schedule is None:
                    raise ValueError("The persisted schedule plan has an invalid timestamp.")
                if playlist.youtube_video_id:
                    services.youtube.update_video_schedule(
                        video_id=playlist.youtube_video_id,
                        scheduled_publish_at=new_schedule,
                        youtube_channel_id=channel_id or None,
                    )
                playlist.metadata_json = _set_schedule_metadata(
                    dict(playlist.metadata_json or {}),
                    new_schedule,
                    request_lane=bool(change.get("request_lane")),
                )
                db.add(playlist)
                change["state"] = "applied"
                change["applied_at"] = _utcnow().isoformat()
                change.pop("error", None)
            except Exception as exc:  # noqa: BLE001
                error = " ".join(str(exc).split())[:500]
                change["state"] = "failed"
                change["error"] = error

        changes[index] = change
        plan["changes"] = changes
        if change.get("state") == "failed":
            plan["status"] = "partial"
            plan["error"] = change.get("error")
            request.schedule_plan_status = "partial"
            request.schedule_plan_json = plan
            request.updated_at = _utcnow()
            db.add(request)
            db.commit()
            raise YouTubeCommentRequestError(
                "The schedule plan was only partially applied and can be resumed safely.",
                code="schedule_apply_partial",
            )
        request.schedule_plan_json = plan
        request.updated_at = _utcnow()
        db.add(request)
        db.commit()

    target_change = next((change for change in changes if change.get("request_lane")), None)
    scheduled_at = _parse_datetime((target_change or {}).get("new_scheduled_publish_at"))
    completed_at = _utcnow()
    plan["status"] = "applied"
    plan["applied_at"] = completed_at.isoformat()
    plan.pop("error", None)
    request.schedule_plan_status = "applied"
    request.schedule_plan_json = plan
    request.scheduled_publish_at = scheduled_at
    request.status = COMPLETED_STATUS
    request.completed_at = completed_at
    request.updated_at = completed_at
    db.add(request)
    db.commit()
    return _schedule_plan_result(request)


def prioritize_comment_request_release(
    db: Session,
    services: ServiceRegistry,
    *,
    release_id: str,
    idempotency_key: str = "",
) -> dict[str, Any]:
    target = db.get(Playlist, str(release_id or "").strip())
    if not target:
        raise YouTubeCommentRequestError("Release not found.", code="release_not_found")
    request = db.scalar(
        select(YouTubeCommentRequest).where(YouTubeCommentRequest.release_id == target.id)
    )
    if not request or request.status not in {PUBLISH_QUEUED_STATUS, COMPLETED_STATUS}:
        raise YouTubeCommentRequestError(
            "Complete the Club Bloom comment request before prioritizing its release.",
            code="request_not_completed",
        )
    if request.schedule_plan_status == "applied":
        return _schedule_plan_result(request)

    target_meta = dict(target.metadata_json or {})
    if not target.output_video_path or not target_meta.get("metadata_approved") or _playlist_is_public(target_meta):
        raise YouTubeCommentRequestError(
            "The request release must be private, rendered, and metadata-approved before prioritization.",
            code="release_not_publish_ready",
        )
    channel_id = str(target_meta.get("youtube_channel_id") or request.youtube_channel_id or "").strip()
    if not _playlist_is_club_bloom(target, channel_id):
        raise YouTubeCommentRequestError(
            "The request release must remain assigned to Club Bloom.",
            code="release_channel_mismatch",
        )

    active_playlist_ids = set(
        db.scalars(
            select(Job.playlist_id).where(
                Job.status.in_([JobStatus.queued, JobStatus.running]),
                Job.type.in_([JobType.build_video, JobType.upload_youtube]),
                Job.playlist_id.is_not(None),
            )
        ).all()
    )
    if target.id in active_playlist_ids:
        raise YouTubeCommentRequestError(
            "The request release still has an active render or upload job.",
            code="release_not_publish_ready",
        )

    if not request.schedule_plan_json:
        _persist_schedule_plan(
            db,
            request,
            target=target,
            channel_id=channel_id,
            idempotency_key=str(idempotency_key or "").strip(),
            now=_utcnow(),
            active_playlist_ids=active_playlist_ids,
            services=services,
        )
    return _apply_schedule_plan(db, services, request)
