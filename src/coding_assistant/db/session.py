import asyncio
from collections.abc import AsyncGenerator
import logging
import os
import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from coding_assistant.config import get_settings
from coding_assistant.db.base import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_database_url(raw_url: str, force_ssl: bool | None = None) -> tuple[str, dict]:
    """
    Ensure the URL uses the asyncpg driver and prepare appropriate connect_args (e.g. SSL).
    """
    url = raw_url
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    connect_args: dict = {}

    ssl_mode = query_params.pop("sslmode", [None])[0]
    ssl_param = query_params.pop("ssl", [None])[0]

    is_local = parsed.hostname in ("localhost", "127.0.0.1", "host.docker.internal", None)
    explicit_disable = ssl_mode == "disable" or ssl_param in ("false", "0", "disable")

    if force_ssl is True or (
        force_ssl is None
        and not explicit_disable
        and (
            not is_local
            or ssl_mode in ("require", "verify-ca", "verify-full")
            or ssl_param in ("require", "true", "1")
        )
    ):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))
    return clean_url, connect_args


def _create_engine(url: str, use_ssl: bool | None = None):
    clean_url, connect_args = normalize_database_url(url, force_ssl=use_ssl)
    return create_async_engine(
        clean_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
    )


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = _create_engine(settings.database_url)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine, _session_factory


async def init_db(max_retries: int = 10, retry_delay: float = 3.0) -> None:
    global _engine, _session_factory
    settings = get_settings()
    parsed = urlparse(settings.database_url)

    is_cloud = bool(os.environ.get("RENDER") or os.environ.get("PORT"))
    is_localhost = parsed.hostname in ("localhost", "127.0.0.1", None)

    if is_localhost and is_cloud:
        logger.error(
            "⚠️ WARNING: DATABASE_URL is pointing to localhost on Render! "
            "Please ensure you created a PostgreSQL database in Render and added "
            "DATABASE_URL in the Web Service Environment Variables."
        )

    # Alternating SSL modes in case the cloud provider internal network prefers non-SSL or SSL
    ssl_sequence = [True, False, True, False, True, False, True, False, True, False]

    for attempt in range(1, max_retries + 1):
        use_ssl = ssl_sequence[(attempt - 1) % len(ssl_sequence)]
        engine = _create_engine(settings.database_url, use_ssl=use_ssl)
        logger.info(
            f"Connecting to database attempt {attempt}/{max_retries} "
            f"[host={parsed.hostname}, port={parsed.port or 5432}, db={parsed.path.lstrip('/')}, ssl={use_ssl}]..."
        )
        try:
            async with engine.begin() as conn:
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                except Exception as ext_err:
                    logger.warning(
                        f"Extension 'vector' notice (may already exist or be managed): {ext_err}"
                    )
                await conn.run_sync(Base.metadata.create_all)
            
            _engine = engine
            _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
            logger.info("✅ Database initialized and schema verified successfully.")
            return
        except Exception as e:
            try:
                await engine.dispose()
            except Exception:
                pass
            if attempt == max_retries:
                logger.error(
                    f"❌ Failed to initialize database after {max_retries} attempts: {e}"
                )
                raise
            logger.warning(
                f"Database connection attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {retry_delay}s (waiting for DB)..."
            )
            await asyncio.sleep(retry_delay)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _, factory = _get_engine()
    assert factory is not None
    async with factory() as session:
        yield session


