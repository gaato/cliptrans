"""Dependency injection factory functions.

Each factory creates an adapter (or service) wired to the current AppConfig.
Entrypoints (CLI, API, Worker) call these to assemble the object graph.
"""

from __future__ import annotations

from cliptrans.config import AppConfig, get_config

# ── Adapters ──────────────────────────────────────────────────────────────────


def make_downloader(config: AppConfig | None = None):
    from cliptrans.adapters.ytdlp import YtdlpDownloader

    return YtdlpDownloader()


def make_media_processor(config: AppConfig | None = None):
    from cliptrans.adapters.ffmpeg import FfmpegMediaProcessor

    return FfmpegMediaProcessor()


def make_transcriber(config: AppConfig | None = None):
    cfg = config or get_config()
    from cliptrans.adapters.asr.faster_whisper import FasterWhisperTranscriber

    return FasterWhisperTranscriber(device=cfg.asr_device, compute_type=cfg.asr_compute_type)


def make_translator(config: AppConfig | None = None):
    cfg = config or get_config()
    from cliptrans.adapters.llm.translation_agent import PydanticAITranslator

    api_key_map = {
        "openai": cfg.openai_api_key,
        "anthropic": cfg.anthropic_api_key,
        "gemini": cfg.gemini_api_key,
        "google": cfg.gemini_api_key,
    }
    api_key = api_key_map.get(cfg.llm_provider.lower())
    return PydanticAITranslator(provider=cfg.llm_provider, model=cfg.llm_model, api_key=api_key)


def make_job_repository(config: AppConfig | None = None):
    cfg = config or get_config()
    from cliptrans.adapters.persistence.repository import SQLAlchemyJobRepository

    return SQLAlchemyJobRepository(database_url=cfg.database_url)


# ── Services ──────────────────────────────────────────────────────────────────


def make_pipeline(config: AppConfig | None = None):
    cfg = config or get_config()
    from cliptrans.application.services.pipeline import PipelineOrchestrator

    return PipelineOrchestrator(
        downloader=make_downloader(cfg),
        media_processor=make_media_processor(cfg),
        transcriber=make_transcriber(cfg),
        translator=make_translator(cfg),
        job_repo=make_job_repository(cfg),
        config=cfg,
    )
