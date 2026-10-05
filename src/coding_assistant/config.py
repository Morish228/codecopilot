from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://assistant:assistant@localhost:5432/assistant",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    routing_config_path: Path = Field(
        default=_PROJECT_ROOT / "routing.config.json",
        alias="ROUTING_CONFIG_PATH",
    )
    routing_default_model: str | None = Field(
        default=None,
        alias="ROUTING_DEFAULT_MODEL",
        description="If set, overrides all tier models (dev/single-model mode).",
    )
    litellm_model: str | None = Field(
        default=None,
        alias="LITELLM_MODEL",
        description="Deprecated: use ROUTING_DEFAULT_MODEL or routing.config.json tiers.",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(
        default=None,
        alias="GEMINI_API_KEY",
        description="Google Gemini API key (LiteLLM provider gemini/).",
    )
    google_api_key: str | None = Field(
        default=None,
        alias="GOOGLE_API_KEY",
        description="Alias for GEMINI_API_KEY accepted by LiteLLM.",
    )
    workspace_root: Path = Field(default=Path("/tmp/workspace"), alias="WORKSPACE_ROOT")
    max_agent_iterations: int = Field(default=10, alias="MAX_AGENT_ITERATIONS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    sandbox_enabled: bool = Field(default=True, alias="SANDBOX_ENABLED")
    sandbox_backend: str = Field(
        default="docker",
        alias="SANDBOX_BACKEND",
        description="docker | local (local is for dev/tests only)",
    )
    sandbox_image: str = Field(
        default="coding-assistant-sandbox:local",
        alias="SANDBOX_IMAGE",
    )
    sandbox_memory_mb: int = Field(default=512, alias="SANDBOX_MEMORY_MB")
    sandbox_cpu_count: float = Field(default=1.0, alias="SANDBOX_CPU_COUNT")
    sandbox_timeout_seconds: int = Field(default=300, alias="SANDBOX_TIMEOUT_SECONDS")
    sandbox_network_enabled: bool = Field(default=False, alias="SANDBOX_NETWORK_ENABLED")
    sandbox_docker_binary: str = Field(default="docker", alias="SANDBOX_DOCKER_BINARY")
    sandbox_max_output_bytes: int = Field(default=65_536, alias="SANDBOX_MAX_OUTPUT_BYTES")
    embedding_model: str | None = Field(default=None, alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=384, alias="EMBEDDING_DIMENSIONS")
    repo_auto_index: bool = Field(default=True, alias="REPO_AUTO_INDEX")
    repo_max_files: int = Field(default=500, alias="REPO_MAX_FILES")
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="coding-assistant", alias="OTEL_SERVICE_NAME")
    otel_exporter: str = Field(default="console", alias="OTEL_EXPORTER")
    otel_otlp_endpoint: str = Field(
        default="http://localhost:4318/v1/traces",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    auth_required: bool = Field(default=False, alias="AUTH_REQUIRED")
    jwt_secret: str = Field(
        default="dev-only-change-me-use-32-plus-chars!!",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60 * 24, alias="JWT_EXPIRE_MINUTES")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    mcp_enabled: bool = Field(default=True, alias="MCP_ENABLED")
    mcp_use_stubs: bool = Field(default=True, alias="MCP_USE_STUBS")
    mcp_agent_tools_enabled: bool = Field(default=False, alias="MCP_AGENT_TOOLS_ENABLED")
    chat_api_base_url: str = Field(
        default="http://127.0.0.1:8000",
        alias="CHAT_API_BASE_URL",
        description="Base URL for `coding-assistant chat` (running serve instance).",
    )
    chat_api_token: str | None = Field(
        default=None,
        alias="CHAT_API_TOKEN",
        description="Optional Bearer token when AUTH_REQUIRED=true.",
    )
    chat_poll_interval_seconds: float = Field(default=1.0, alias="CHAT_POLL_INTERVAL_SECONDS")
    chat_run_timeout_seconds: int = Field(default=300, alias="CHAT_RUN_TIMEOUT_SECONDS")

    @model_validator(mode="after")
    def _compat_litellm_model(self) -> "Settings":
        if self.routing_default_model is None and self.litellm_model:
            self.routing_default_model = self.litellm_model
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
