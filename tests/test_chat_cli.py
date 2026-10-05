import json
import uuid

import httpx
import pytest

from coding_assistant.cli.chat import parse_slash_command
from coding_assistant.cli.client import ApiClient, ApiError


def test_parse_slash_command():
    assert parse_slash_command("/exit") == ("exit", "")
    assert parse_slash_command("/workspace /tmp/foo") == ("workspace", "/tmp/foo")
    assert parse_slash_command("hello") == (None, "hello")


def _mock_transport() -> httpx.MockTransport:
    run_id = uuid.uuid4()
    state = {"status": "running", "polls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/runs" and request.method == "POST":
            return httpx.Response(
                202,
                json={
                    "id": str(run_id),
                    "status": "running",
                    "workspace_root": "/w",
                    "user_message": "hi",
                    "final_response": None,
                    "error": None,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                },
            )
        if request.url.path == f"/v1/runs/{run_id}":
            state["polls"] += 1
            if state["polls"] < 2:
                status = "running"
                final = None
            else:
                status = "completed"
                final = "done"
            return httpx.Response(
                200,
                json={
                    "id": str(run_id),
                    "status": status,
                    "workspace_root": "/w",
                    "user_message": "hi",
                    "final_response": final,
                    "error": None,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


def test_client_wait_for_run_completed():
    transport = _mock_transport()
    with httpx.Client(transport=transport, base_url="http://test") as http:
        client = ApiClient("http://test")
        client._http = http  # noqa: SLF001
        run = client.create_run("/w", "hi")
        finished = client.wait_for_run(run.id, poll_interval=0.01, timeout_seconds=5)
    assert finished.status == "completed"
    assert finished.final_response == "done"


def test_client_health_false_on_error():
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    with httpx.Client(transport=transport, base_url="http://test") as http:
        client = ApiClient("http://test")
        client._http = http  # noqa: SLF001
        assert client.health() is False


def test_client_create_run_error():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(400, json={"detail": "bad request"}),
    )
    with httpx.Client(transport=transport, base_url="http://test") as http:
        client = ApiClient("http://test")
        client._http = http  # noqa: SLF001
        with pytest.raises(ApiError):
            client.create_run("/w", "x")
