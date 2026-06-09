from __future__ import annotations

from functools import lru_cache
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def _get_engine():
    url = settings.DB_URL
    is_sqlite = url.startswith("sqlite")
    kwargs = {"echo": settings.APP_ENV == "development", "pool_pre_ping": not is_sqlite}
    if not is_sqlite:
        kwargs.update({"pool_size": 10, "max_overflow": 20})
    return create_async_engine(url, **kwargs)


@lru_cache(maxsize=1)
def _get_dos_engine():
    url = settings.DOS_DB_URL
    is_sqlite = url.startswith("sqlite")
    kwargs = {"echo": False, "pool_pre_ping": not is_sqlite}
    if not is_sqlite:
        kwargs["pool_size"] = 5
    return create_async_engine(url, **kwargs)


def _get_session_factory():
    return async_sessionmaker(_get_engine(), expire_on_commit=False)


def _get_dos_session_factory():
    return async_sessionmaker(_get_dos_engine(), expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with _get_session_factory()() as session:
        yield session


async def get_dos_db() -> AsyncSession:
    async with _get_dos_session_factory()() as session:
        yield session
