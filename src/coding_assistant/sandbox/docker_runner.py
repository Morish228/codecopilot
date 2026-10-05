import asyncio
import logging
import time
from pathlib import Path

from coding_assistant.sandbox.types import SandboxConfig, SandboxResult
from coding_assistant.tools.errors import ToolExecutionError

logger = logging.getLogger(__name__)


class DockerSandboxRunner:
    """Runs allowlisted argv in an isolated Docker container (network off by default)."""

    def __init__(self, config: SandboxConfig) -> None:
        self._config = config

    async def run(
        self,
        workspace_root: Path,
        argv: list[str],
        *,
        network_enabled: bool | None = None,
    ) -> SandboxResult:
        workspace = workspace_root.resolve()
        if not workspace.is_dir():
            raise ToolExecutionError(f"Workspace is not a directory: {workspace}")

        network = network_enabled if network_enabled is not None else self._config.network_enabled
        docker_cmd = self._build_run_command(workspace, argv, network)

        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._config.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ToolExecutionError(
                f"Sandbox timed out after {self._config.timeout_seconds}s"
            ) from exc
        except FileNotFoundError as exc:
            raise ToolExecutionError(
                f"Docker binary not found: {self._config.docker_binary}"
            ) from exc

        duration_ms = (time.perf_counter() - started) * 1000
        stdout = _truncate(stdout_b.decode("utf-8", errors="replace"), self._config.max_output_bytes)
        stderr = _truncate(stderr_b.decode("utf-8", errors="replace"), self._config.max_output_bytes)

        return SandboxResult(
            exit_code=proc.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            backend="docker",
        )

    def _build_run_command(self, workspace: Path, argv: list[str], network_enabled: bool) -> list[str]:
        network_mode = "bridge" if network_enabled else "none"
        return [
            self._config.docker_binary,
            "run",
            "--rm",
            "--network",
            network_mode,
            "--memory",
            f"{self._config.memory_mb}m",
            "--cpus",
            str(self._config.cpu_count),
            "-v",
            f"{workspace}:/workspace:rw",
            "-w",
            "/workspace",
            self._config.image,
            *argv,
        ]


async def docker_available(docker_binary: str = "docker") -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            docker_binary,
            "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _truncate(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n... [truncated]"
