from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLIPTRANS_",
        env_file=".env",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: init > env > .env > glossary.toml > cliptrans.toml
        toml_source = TomlConfigSettingsSource(
            settings_cls, toml_file=["cliptrans.toml", "glossary.toml"]
        )
        return (init_settings, env_settings, dotenv_settings, toml_source)

    # Data storage
    data_dir: Path = Field(default=Path("data"), description="Root data directory")

    # ASR defaults
    asr_model: str = Field(default="large-v3", description="Whisper model name")
    asr_device: str = Field(default="cuda", description="Device: cuda or cpu")
    asr_compute_type: str = Field(default="float16", description="Compute type for CTranslate2")

    # Translation defaults
    llm_provider: str = Field(default="openai", description="LLM provider name")
    llm_model: str = Field(default="gpt-4o", description="LLM model name")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    gemini_api_key: str | None = Field(default=None, description="Gemini API key")

    # Pipeline defaults
    source_language: str = Field(default="ja")
    target_language: str = Field(default="en")

    # Proper noun support
    asr_corrections: dict[str, str] = Field(
        default_factory=dict,
        description="Post-ASR text substitutions applied before regroup: wrong → correct",
    )
    glossary: dict[str, str] = Field(
        default_factory=dict,
        description="Translation glossary passed to LLM: source term → target term",
    )

    # Regroup thresholds
    regroup_silence_threshold: float = Field(
        default=1.0, description="Silence gap in seconds to split utterances"
    )
    regroup_max_chars: int = Field(
        default=200, description="Max characters per utterance before forced split"
    )

    # Translation batching
    translate_chunk_size: int = Field(default=10, description="Utterances per translation batch")
    translate_context_size: int = Field(
        default=3, description="Previous utterances to include as context"
    )

    # DB
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/db.sqlite3",
        description="SQLAlchemy async database URL",
    )

    # Holodex
    holodex_api_key: str | None = Field(default=None, description="Holodex API key")
    holodex_default_org: str | None = Field(default=None, description="Default org filter")

    # Clip Finder
    clip_finder_chunk_minutes: float = Field(
        default=10.0, description="Subtitle chunk window (minutes)"
    )
    clip_finder_overlap_minutes: float = Field(default=1.0, description="Chunk overlap (minutes)")
    clip_finder_max_candidates: int = Field(default=20, description="Max candidates per stream")

    # Web UI
    web_host: str = Field(default="127.0.0.1", description="Web server host")
    web_port: int = Field(default=8000, description="Web server port")


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config() -> None:
    """Reset cached config (useful in tests)."""
    global _config
    _config = None
