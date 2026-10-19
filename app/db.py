import json
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.base import Base
from app.utils.track_search import ensure_track_search_schema, refresh_track_search_index_if_needed

_engine: Engine | None = None
_session_local: sessionmaker | None = None
_database_url: str | None = None


def _ensure_engine() -> tuple[Engine, sessionmaker]:
    global _engine, _session_local, _database_url

    settings = get_settings()
    if _engine is not None and _session_local is not None and _database_url == settings.database_url:
        return _engine, _session_local

    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 2

    engine_kwargs = {"connect_args": connect_args}
    if settings.database_url.startswith("sqlite"):
        # Render-worker progress and chunk-upload requests can briefly arrive in
        # bursts. Keep enough pooled handles for concurrent reads, but fail fast
        # instead of letting browser requests wait behind the default 30s pool
        # timeout when a worker storm exhausts the pool.
        engine_kwargs.update(pool_size=8, max_overflow=4, pool_timeout=2)

    _engine = create_engine(settings.database_url, **engine_kwargs)
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(_engine, "first_connect")
        def _enable_sqlite_wal(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            # WAL is persistent for a file-backed database. Reapplying this
            # pragma on every pooled connection can contend with active writes.
            dbapi_connection.execute("PRAGMA busy_timeout=2000")
            dbapi_connection.execute("PRAGMA journal_mode=WAL")

        @event.listens_for(_engine, "connect")
        def _set_sqlite_busy_timeout(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            dbapi_connection.execute("PRAGMA busy_timeout=2000")
            dbapi_connection.execute("PRAGMA synchronous=NORMAL")

    _session_local = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _database_url = settings.database_url
    return _engine, _session_local


def init_db() -> None:
    import app.models  # noqa: F401

    engine, _ = _ensure_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_youtube_comment_request_schema(engine)
    ensure_track_search_schema(engine)
    with Session(bind=engine) as db:
        refresh_track_search_index_if_needed(db, commit=True, force=True)


def _ensure_youtube_comment_request_schema(engine: Engine) -> None:
    """Upgrade the short-lived pilot table created by an earlier app build."""
    inspector = inspect(engine)
    table_name = "youtube_comment_requests"
    with engine.begin() as connection:
        if "playlists" in inspector.get_table_names():
            playlist_columns = {
                column["name"] for column in inspector.get_columns("playlists")
            }
            if "youtube_comment_request_id" not in playlist_columns:
                try:
                    connection.execute(
                        text(
                            "ALTER TABLE playlists ADD COLUMN "
                            "youtube_comment_request_id VARCHAR(36)"
                        )
                    )
                except OperationalError as exc:
                    if "duplicate column" not in str(exc).lower():
                        raise
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "ix_playlists_youtube_comment_request_id "
                    "ON playlists (youtube_comment_request_id) "
                    "WHERE youtube_comment_request_id IS NOT NULL"
                )
            )
    if table_name not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    additions = {
        "request_summary": "VARCHAR(500) NOT NULL DEFAULT ''",
        "queue_rank": "INTEGER NOT NULL DEFAULT 0",
        "claim_expires_at": "DATETIME",
        "operation_results_json": "JSON NOT NULL DEFAULT '{}'",
        "completion_idempotency_key": "VARCHAR(255)",
        "defer_idempotency_key": "VARCHAR(255)",
        "schedule_plan_key": "VARCHAR(255)",
        "schedule_plan_status": "VARCHAR(32)",
        "schedule_plan_json": "JSON NOT NULL DEFAULT '{}'",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                try:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {name} {definition}")
                    )
                except OperationalError as exc:
                    if "duplicate column" not in str(exc).lower():
                        raise

        rows = connection.execute(
            text(
                "SELECT id, youtube_channel_id, requested_genres_json, requested_mood, "
                "requested_duration_seconds, request_summary, queue_rank, created_at "
                f"FROM {table_name} ORDER BY youtube_channel_id, created_at, id"
            )
        ).mappings().all()
        rank_by_channel: dict[str, int] = {}
        for row in rows:
            channel_id = str(row["youtube_channel_id"] or "")
            rank_by_channel[channel_id] = rank_by_channel.get(channel_id, 0) + 1
            summary = str(row["request_summary"] or "").strip()
            if not summary:
                raw_genres = row["requested_genres_json"]
                if isinstance(raw_genres, str):
                    try:
                        raw_genres = json.loads(raw_genres)
                    except json.JSONDecodeError:
                        raw_genres = []
                genres = " + ".join(str(value) for value in (raw_genres or []) if str(value).strip())
                mood = str(row["requested_mood"] or "instrumental")
                minutes = max(int(row["requested_duration_seconds"] or 3600) // 60, 1)
                summary = f"{genres or 'Club music'} | {mood} | {minutes} min"[:500]
            connection.execute(
                text(
                    f"UPDATE {table_name} "
                    "SET queue_rank = :queue_rank, request_summary = :request_summary "
                    "WHERE id = :request_id"
                ),
                {
                    "queue_rank": rank_by_channel[channel_id],
                    "request_summary": summary,
                    "request_id": row["id"],
                },
            )

        connection.execute(
            text(
                "UPDATE playlists SET youtube_comment_request_id = ("
                f"SELECT id FROM {table_name} "
                "WHERE release_id = playlists.id ORDER BY created_at, id LIMIT 1"
                ") WHERE youtube_comment_request_id IS NULL AND EXISTS ("
                f"SELECT 1 FROM {table_name} WHERE release_id = playlists.id"
                ")"
            )
        )

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_comment_requests_channel_comment_idx "
                f"ON {table_name} (youtube_channel_id, comment_id)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_comment_requests_channel_queue_rank_idx "
                f"ON {table_name} (youtube_channel_id, queue_rank)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_comment_requests_release_idx "
                f"ON {table_name} (release_id) WHERE release_id IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_youtube_comment_requests_active_queue "
                f"ON {table_name} (channel_title, status, queue_rank)"
            )
        )


def SessionLocal() -> Session:  # noqa: N802
    _, session_local = _ensure_engine()
    return session_local()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
