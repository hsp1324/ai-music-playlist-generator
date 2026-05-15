from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.base import Base

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
        connect_args["timeout"] = 60

    _engine = create_engine(settings.database_url, connect_args=connect_args)
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _set_sqlite_busy_timeout(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            dbapi_connection.execute("PRAGMA busy_timeout=60000")

    _session_local = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    _database_url = settings.database_url
    return _engine, _session_local


def init_db() -> None:
    import app.models  # noqa: F401

    engine, _ = _ensure_engine()
    Base.metadata.create_all(bind=engine)


def SessionLocal() -> Session:  # noqa: N802
    _, session_local = _ensure_engine()
    return session_local()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
