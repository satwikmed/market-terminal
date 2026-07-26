import re
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Coerce provider-supplied Postgres URLs into an async SQLAlchemy DSN.

    Render and Heroku hand out `postgres://` URLs, which SQLAlchemy rejects, and
    the sync `postgresql://` form would pick a blocking driver.
    """
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    # asyncpg negotiates TLS itself and rejects libpq's sslmode parameter.
    if "+asyncpg" in url and "sslmode=" in url:
        url = re.sub(r"[?&]sslmode=[^&]*", "", url)
    return url


settings = get_settings()
DATABASE_URL = normalize_database_url(settings.database_url)
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
