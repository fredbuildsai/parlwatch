from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from parlwatch.db.models import Base
from parlwatch.settings import get_settings


def make_engine(url: str | None = None):
    url = url or get_settings().database_url
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


def init_db(url: str | None = None) -> None:
    Base.metadata.create_all(make_engine(url))


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    session = sessionmaker(make_engine(url), expire_on_commit=False)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
