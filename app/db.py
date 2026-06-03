from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
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
        engine_kwargs.update(pool_size=20, max_overflow=20, pool_timeout=2)

    _engine = create_engine(settings.database_url, **engine_kwargs)
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _set_sqlite_busy_timeout(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            dbapi_connection.execute("PRAGMA busy_timeout=2000")
            dbapi_connection.execute("PRAGMA journal_mode=WAL")
            dbapi_connection.execute("PRAGMA synchronous=NORMAL")

    _session_local = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _database_url = settings.database_url
    return _engine, _session_local


def init_db() -> None:
    import app.models  # noqa: F401

    engine, _ = _ensure_engine()
    Base.metadata.create_all(bind=engine)
    ensure_track_search_schema(engine)
    with Session(bind=engine) as db:
        refresh_track_search_index_if_needed(db, commit=True, force=True)


def SessionLocal() -> Session:  # noqa: N802
    _, session_local = _ensure_engine()
    return session_local()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
