from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from app.env import load_local_env


SUPPORTED_PROVIDERS = ("mock", "openai", "anthropic", "google", "bedrock")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _get_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    debug: bool
    log_level: str
    cors_origins: tuple[str, ...]
    max_message_chars: int
    default_provider: str
    openai_model: str
    anthropic_model: str
    google_model: str
    bedrock_model: str
    aws_region: str
    request_timeout_seconds: int
    source_max_bytes: int
    use_local_rag: bool
    kb_chunks_path: Path
    enable_debug_traces: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_local_env()
        backend_root = Path(__file__).resolve().parents[1]
        default_provider = os.getenv("DEFAULT_PROVIDER", "mock").strip().lower()
        if default_provider not in SUPPORTED_PROVIDERS:
            default_provider = "mock"
        return cls(
            app_name=os.getenv("APP_NAME", "caishen"),
            app_env=os.getenv("APP_ENV", "local"),
            debug=_get_bool("DEBUG", True),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cors_origins=_get_tuple(
                "CORS_ORIGINS",
                ("http://localhost:3000", "http://127.0.0.1:3000"),
            ),
            max_message_chars=_get_int("MAX_MESSAGE_CHARS", 4000),
            default_provider=default_provider,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
            google_model=os.getenv("GOOGLE_MODEL", "gemini-2.0-flash"),
            bedrock_model=os.getenv(
                "BEDROCK_MODEL_ID",
                "anthropic.claude-3-5-haiku-20241022-v1:0",
            ),
            aws_region=os.getenv("AWS_REGION", "eu-west-2"),
            request_timeout_seconds=_get_int("REQUEST_TIMEOUT_SECONDS", 20),
            source_max_bytes=_get_int("SOURCE_MAX_BYTES", 1_000_000),
            use_local_rag=_get_bool("USE_LOCAL_RAG", True),
            kb_chunks_path=Path(
                os.getenv(
                    "KB_CHUNKS_PATH",
                    str(backend_root / "kb" / "processed_docs" / "chunks.jsonl"),
                )
            ),
            enable_debug_traces=_get_bool("ENABLE_DEBUG_TRACES", True),
        )

    def model_for(self, provider: str) -> str:
        models = {
            "mock": "caishen-mock",
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "google": self.google_model,
            "bedrock": self.bedrock_model,
        }
        return models[provider]

    def configured_providers(self) -> tuple[str, ...]:
        providers = ["mock", "bedrock"]
        if os.getenv("OPENAI_API_KEY"):
            providers.append("openai")
        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append("anthropic")
        if os.getenv("GOOGLE_API_KEY"):
            providers.append("google")
        return tuple(providers)
