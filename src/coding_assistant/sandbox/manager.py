import logging
from pathlib import Path

from coding_assistant.config import Settings, get_settings
from coding_assistant.sandbox.commands import parse_allowlisted_command
from coding_assistant.sandbox.docker_runner import DockerSandboxRunner, docker_available
from coding_assistant.sandbox.local_runner import LocalSandboxRunner
from coding_assistant.sandbox.types import SandboxConfig, SandboxResult
from coding_assistant.tools.errors import ToolExecutionError

logger = logging.getLogger(__name__)


class SandboxManager:
    """High-level API: run allowlisted commands in an isolated environment."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._config = SandboxConfig(
            image=self._settings.sandbox_image,
            memory_mb=self._settings.sandbox_memory_mb,
            cpu_count=self._settings.sandbox_cpu_count,
            timeout_seconds=self._settings.sandbox_timeout_seconds,
            network_enabled=self._settings.sandbox_network_enabled,
            docker_binary=self._settings.sandbox_docker_binary,
            max_output_bytes=self._settings.sandbox_max_output_bytes,
        )
        backend = self._settings.sandbox_backend.lower()
        if backend == "docker":
            self._runner = DockerSandboxRunner(self._config)
        elif backend == "local":
            self._runner = LocalSandboxRunner(self._config)
        else:
            raise ToolExecutionError(f"Unknown sandbox backend: {backend}")

    async def run_tests(
        self,
        workspace_root: Path,
        command: str,
        *,
        network_enabled: bool | None = None,
    ) -> SandboxResult:
        if not self._settings.sandbox_enabled:
            raise ToolExecutionError("Sandbox is disabled (SANDBOX_ENABLED=false)")

        argv = parse_allowlisted_command(command)

        if self._settings.sandbox_backend.lower() == "docker":
            if not await docker_available(self._config.docker_binary):
                raise ToolExecutionError(
                    "Docker is not available. Build the sandbox image or set SANDBOX_BACKEND=local for dev."
                )

        logger.info(
            "Sandbox run workspace=%s argv=%s backend=%s",
            workspace_root,
            argv,
            self._settings.sandbox_backend,
        )
        return await self._runner.run(
            workspace_root,
            argv,
            network_enabled=network_enabled,
        )

    async def run_argv(
        self,
        workspace_root: Path,
        argv: list[str],
        *,
        network_enabled: bool | None = None,
    ) -> SandboxResult:
        """Run fixed argv after explicit user approval (bypasses allowlist)."""
        if not self._settings.sandbox_enabled:
            raise ToolExecutionError("Sandbox is disabled (SANDBOX_ENABLED=false)")
        if not argv:
            raise ToolExecutionError("Empty argv")
        return await self._runner.run(workspace_root, argv, network_enabled=network_enabled)


_manager: SandboxManager | None = None


def get_sandbox_manager() -> SandboxManager:
    global _manager
    if _manager is None:
        _manager = SandboxManager()
    return _manager


def reset_sandbox_manager() -> None:
    global _manager
    _manager = None
