import asyncio
import sys
import time
from pathlib import Path

from coding_assistant.sandbox.types import SandboxConfig, SandboxResult
from coding_assistant.tools.errors import ToolExecutionError


class LocalSandboxRunner:
    """Dev/test fallback: subprocess in workspace without shell (no container isolation)."""

    def __init__(self, config: SandboxConfig) -> None:
        self._config = config

    async def run(
        self,
        workspace_root: Path,
        argv: list[str],
        *,
        network_enabled: bool | None = None,
    ) -> SandboxResult:
        if network_enabled:
            raise ToolExecutionError("Local sandbox backend does not allow network access")

        workspace = workspace_root.resolve()
        exec_argv = _resolve_local_argv(argv)
        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_argv,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._config.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ToolExecutionError(
                f"Command timed out after {self._config.timeout_seconds}s"
            ) from exc
        except FileNotFoundError as exc:
            raise ToolExecutionError(f"Executable not found: {exec_argv[0]}") from exc

        duration_ms = (time.perf_counter() - started) * 1000
        max_bytes = self._config.max_output_bytes
        stdout = _truncate(stdout_b.decode("utf-8", errors="replace"), max_bytes)
        stderr = _truncate(stderr_b.decode("utf-8", errors="replace"), max_bytes)

        return SandboxResult(
            exit_code=proc.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            backend="local",
        )


def _resolve_local_argv(argv: list[str]) -> list[str]:
    """Map allowlisted pytest invocations to the current interpreter."""
    if argv and argv[0] == "pytest":
        return [sys.executable, "-m", "pytest", *argv[1:]]
    if len(argv) >= 3 and argv[0] == "python" and argv[1] == "-m":
        return [sys.executable, *argv[1:]]
    return argv


def _truncate(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n... [truncated]"
