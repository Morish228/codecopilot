import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from coding_assistant.config import get_settings
from coding_assistant.sandbox.commands import parse_allowlisted_command
from coding_assistant.sandbox.docker_runner import DockerSandboxRunner
from coding_assistant.sandbox.manager import SandboxManager, reset_sandbox_manager
from coding_assistant.sandbox.types import SandboxConfig, SandboxResult
from coding_assistant.tools.errors import ApprovalRequiredError


@pytest.fixture(autouse=True)
def _reset():
    reset_sandbox_manager()
    get_settings.cache_clear()
    yield
    reset_sandbox_manager()
    get_settings.cache_clear()


def test_parse_allowlisted_command_to_argv():
    assert parse_allowlisted_command("pytest -q") == ["pytest", "-q"]


def test_parse_rejects_unknown_command():
    with pytest.raises(ApprovalRequiredError):
        parse_allowlisted_command("rm -rf /")


def test_docker_run_command_uses_network_none():
    config = SandboxConfig(
        image="coding-assistant-sandbox:local",
        memory_mb=512,
        cpu_count=1.0,
        timeout_seconds=60,
        network_enabled=False,
    )
    runner = DockerSandboxRunner(config)
    cmd = runner._build_run_command(Path("/tmp/ws").resolve(), ["pytest", "-q"], False)
    assert "--network" in cmd
    assert "none" in cmd
    assert "--memory" in cmd
    assert "512m" in cmd


@pytest.mark.asyncio
async def test_sandbox_manager_runs_via_docker_runner(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_BACKEND", "docker")
    get_settings.cache_clear()
    reset_sandbox_manager()

    fake_result = SandboxResult(
        exit_code=0,
        stdout="1 passed\n",
        stderr="",
        duration_ms=12.5,
        backend="docker",
    )

    with patch(
        "coding_assistant.sandbox.manager.docker_available",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with patch.object(DockerSandboxRunner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = fake_result
            manager = SandboxManager()
            result = await manager.run_tests(tmp_path, "pytest -q")

    assert result.exit_code == 0
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_tests_tool_uses_sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_BACKEND", "local")
    get_settings.cache_clear()
    reset_sandbox_manager()

    (tmp_path / "test_ok.py").write_text(
        "def test_x():\n    assert True\n",
        encoding="utf-8",
    )

    from coding_assistant.tools.handlers import handle_run_tests

    out = await handle_run_tests(tmp_path, {"command": "pytest -q"})
    assert out["sandbox"] == "local"
    assert out["exit_code"] == 0
    assert out["status"] == "passed"


@pytest.mark.asyncio
async def test_docker_runner_invokes_subprocess(tmp_path):
    config = SandboxConfig(
        image="coding-assistant-sandbox:local",
        memory_mb=256,
        cpu_count=0.5,
        timeout_seconds=30,
        network_enabled=False,
    )
    runner = DockerSandboxRunner(config)

    class FakeProc:
        returncode = 0

        async def communicate(self):
            return b"ok\n", b""

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = FakeProc()
        result = await runner.run(tmp_path, ["echo", "ok"])

    assert result.exit_code == 0
    assert "ok" in result.stdout
    args = mock_exec.await_args[0]
    assert args[0] == "docker"
    assert "none" in args
