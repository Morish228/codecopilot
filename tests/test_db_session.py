import pytest
from coding_assistant.db.session import normalize_database_url


def test_normalize_postgres_scheme_localhost():
    url, connect_args = normalize_database_url("postgres://user:pass@localhost:5432/testdb")
    assert url == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
    assert connect_args == {}


def test_normalize_postgresql_scheme_localhost():
    url, connect_args = normalize_database_url("postgresql://user:pass@127.0.0.1:5432/testdb")
    assert url == "postgresql+asyncpg://user:pass@127.0.0.1:5432/testdb"
    assert connect_args == {}


def test_normalize_render_internal_host_codecopilot_db():
    raw = "postgres://assistant:secret123@codecopilot-db:5432/assistant"
    url, connect_args = normalize_database_url(raw)
    assert url == "postgresql+asyncpg://assistant:secret123@codecopilot-db:5432/assistant"
    assert "ssl" in connect_args
    assert connect_args["ssl"] is not None


def test_normalize_render_internal_host_dpg():
    raw = "postgres://assistant:secret123@dpg-c1234567-a:5432/assistant"
    url, connect_args = normalize_database_url(raw)
    assert url == "postgresql+asyncpg://assistant:secret123@dpg-c1234567-a:5432/assistant"
    assert "ssl" in connect_args
    assert connect_args["ssl"] is not None


def test_normalize_render_external_url_with_ssl():
    raw = "postgres://user:pass@dpg-abc12345-a.oregon-postgres.render.com:5432/assistant?sslmode=require"
    url, connect_args = normalize_database_url(raw)
    assert url.startswith("postgresql+asyncpg://user:pass@dpg-abc12345-a.oregon-postgres.render.com:5432/assistant")
    assert "sslmode" not in url
    assert "ssl" in connect_args
    assert connect_args["ssl"] is not None


def test_normalize_ssl_disabled():
    raw = "postgresql+asyncpg://user:pass@remotehost:5432/assistant?sslmode=disable"
    url, connect_args = normalize_database_url(raw)
    assert "sslmode" not in url
    assert connect_args == {}
