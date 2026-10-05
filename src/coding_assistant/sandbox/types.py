from pydantic import BaseModel, ConfigDict, Field


class SandboxResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    backend: str = Field(description="docker | local")


class SandboxConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: str
    memory_mb: int
    cpu_count: float
    timeout_seconds: int
    network_enabled: bool
    docker_binary: str = "docker"
    max_output_bytes: int = 65_536
