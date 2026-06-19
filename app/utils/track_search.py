import re
import time
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.track import Track
from app.utils.track_titles import clean_track_display_title, upload_track_title

TRACK_SEARCH_FTS_TABLE = "track_search_fts"
TRACK_SEARCH_PREFIX_LENGTHS = "1 2 3 4"
SEARCH_TOKEN_RE = re.compile(r"[\w]+", flags=re.UNICODE)
INDEX_CHECK_INTERVAL_SECONDS = 30.0
_last_index_check_at = 0.0


def _search_value(value: object, *, max_chars: int = 4000) -> str:
    text_value = str(value or "")
    if len(text_value) <= max_chars:
        return text_value
    return text_value[:max_chars]


def ensure_track_search_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_tracks_created_at ON tracks(created_at)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_tracks_title_nocase ON tracks(title COLLATE NOCASE)")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_tracks_user_rating "
            "ON tracks(json_extract(metadata_json, '$.user_rating'))"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status_type_created_at "
            "ON jobs(status, type, created_at)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_jobs_type_status_started_at "
            "ON jobs(type, status, started_at)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_playlists_status_updated_at "
            "ON playlists(status, updated_at)"
        )
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_playlists_updated_at ON playlists(updated_at)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_playlists_created_at ON playlists(created_at)")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_playlists_youtube_video_id "
            "ON playlists(youtube_video_id)"
        )
        connection.exec_driver_sql(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {TRACK_SEARCH_FTS_TABLE} USING fts5(
                track_id UNINDEXED,
                title,
                title_clean,
                prompt,
                style,
                exclude_style,
                tags,
                lyrics,
                source_track_id,
                audio_path,
                preview_url,
                source_playlist_title,
                source_youtube_video_id,
                tokenize = 'unicode61',
                prefix = '{TRACK_SEARCH_PREFIX_LENGTHS}'
            )
            """
        )


def searchable_track_values(track: Track) -> dict[str, str]:
    meta = dict(track.metadata_json or {})
    return {
        "track_id": str(track.id or ""),
        "title": str(track.title or ""),
        "title_clean": " ".join(
            value
            for value in (
                clean_track_display_title(track.title),
                upload_track_title(track.title),
            )
            if value
        ),
        "prompt": _search_value(track.prompt, max_chars=3000),
        "style": _search_value(meta.get("style"), max_chars=1200),
        "exclude_style": _search_value(meta.get("exclude_style"), max_chars=1200),
        "tags": _search_value(meta.get("tags"), max_chars=1200),
        "lyrics": _search_value(meta.get("lyrics"), max_chars=3000),
        "source_track_id": str(track.source_track_id or ""),
        "audio_path": str(track.audio_path or ""),
        "preview_url": str(track.preview_url or ""),
        "source_playlist_title": str(meta.get("source_playlist_title") or meta.get("pending_workspace_title") or ""),
        "source_youtube_video_id": str(meta.get("source_youtube_video_id") or ""),
    }


def build_track_search_text(track: Track) -> str:
    return " ".join(searchable_track_values(track).values()).casefold()


def normalize_track_search_terms(query: str | None, *, max_terms: int = 8) -> list[str]:
    raw_terms = SEARCH_TOKEN_RE.findall(str(query or "").casefold())
    terms: list[str] = []
    for term in raw_terms:
        if not term or term in terms:
            continue
        terms.append(term)
        if len(terms) >= max_terms:
            break
    return terms


def track_matches_terms(track: Track, terms: Iterable[str]) -> bool:
    term_list = list(terms)
    if not term_list:
        return True
    haystack = build_track_search_text(track)
    return all(term in haystack for term in term_list)


def _fts_match_query(terms: Iterable[str]) -> str:
    return " AND ".join(f"{term}*" for term in terms if term)


def sync_track_search_document(db: Session, track: Track) -> None:
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return
    values = searchable_track_values(track)
    db.execute(
        text(f"DELETE FROM {TRACK_SEARCH_FTS_TABLE} WHERE track_id = :track_id"),
        {"track_id": values["track_id"]},
    )
    db.execute(
        text(
            f"""
            INSERT INTO {TRACK_SEARCH_FTS_TABLE} (
                track_id,
                title,
                title_clean,
                prompt,
                style,
                exclude_style,
                tags,
                lyrics,
                source_track_id,
                audio_path,
                preview_url,
                source_playlist_title,
                source_youtube_video_id
            ) VALUES (
                :track_id,
                :title,
                :title_clean,
                :prompt,
                :style,
                :exclude_style,
                :tags,
                :lyrics,
                :source_track_id,
                :audio_path,
                :preview_url,
                :source_playlist_title,
                :source_youtube_video_id
            )
            """
        ),
        values,
    )


def rebuild_track_search_index(db: Session) -> None:
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return
    db.execute(text(f"DELETE FROM {TRACK_SEARCH_FTS_TABLE}"))
    for track in db.scalars(select(Track)).all():
        sync_track_search_document(db, track)


def refresh_track_search_index_if_needed(db: Session, *, commit: bool = False, force: bool = False) -> None:
    global _last_index_check_at

    if db.bind is None or db.bind.dialect.name != "sqlite":
        return
    now = time.monotonic()
    if not force and now - _last_index_check_at < INDEX_CHECK_INTERVAL_SECONDS:
        return
    try:
        track_count = int(db.scalar(select(func.count(Track.id))) or 0)
        indexed_count = int(db.execute(text(f"SELECT count(*) FROM {TRACK_SEARCH_FTS_TABLE}")).scalar() or 0)
    except SQLAlchemyError:
        if commit:
            db.rollback()
        return
    _last_index_check_at = now
    if track_count == indexed_count:
        return
    rebuild_track_search_index(db)
    if commit:
        db.commit()


def search_track_ids(db: Session, query: str | None, *, limit: int = 500) -> list[str]:
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return []
    terms = normalize_track_search_terms(query)
    match_query = _fts_match_query(terms)
    if not match_query:
        return []
    refresh_track_search_index_if_needed(db, commit=True)
    try:
        rows = db.execute(
            text(
                f"""
                SELECT track_id
                FROM {TRACK_SEARCH_FTS_TABLE}
                WHERE {TRACK_SEARCH_FTS_TABLE} MATCH :match_query
                ORDER BY bm25({TRACK_SEARCH_FTS_TABLE})
                LIMIT :limit
                """
            ),
            {"match_query": match_query, "limit": max(int(limit or 0), 1)},
        ).all()
    except SQLAlchemyError:
        db.rollback()
        return []
    return [str(row[0]) for row in rows if row[0]]


def best_track_match_text(track: Track, query: str | None) -> tuple[str, str]:
    terms = normalize_track_search_terms(query)
    values = searchable_track_values(track)
    preferred_fields = (
        ("title", values["title"]),
        ("style", values["style"]),
        ("tags", values["tags"]),
        ("prompt", values["prompt"]),
        ("lyrics", values["lyrics"]),
        ("source_playlist", values["source_playlist_title"]),
    )
    for field, value in preferred_fields:
        folded = value.casefold()
        if value and any(term in folded for term in terms):
            return field, value
    return "title", values["title"]


def user_rating_filter_expression(user_rating: str | None) -> Any | None:
    if user_rating not in {"like", "dislike"}:
        return None
    return func.json_extract(Track.metadata_json, "$.user_rating") == user_rating
