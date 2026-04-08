"""Dependency injection factory functions.

Each factory creates an adapter (or service) wired to the current AppConfig.
Entrypoints (CLI, API, Worker) call these to assemble the object graph.
"""

from __future__ import annotations

from cliptrans.config import AppConfig, get_config

# Adapters


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


# Services


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


def make_holodex(config: AppConfig | None = None):
    cfg = config or get_config()
    if cfg.holodex_api_key:
        from cliptrans.adapters.holodex import HolodexAdapter

        return HolodexAdapter(cfg.holodex_api_key)
    from cliptrans.adapters.holodex import _StubHolodex

    return _StubHolodex()


def make_clip_finder_service(config: AppConfig | None = None):
    cfg = config or get_config()
    from cliptrans.adapters.llm.clip_finder_agent import ClipFinderAgent
    from cliptrans.adapters.subtitle_fetcher import YtdlpSubtitleFetcher
    from cliptrans.application.services.clip_finder import ClipFinderService

    agent = ClipFinderAgent(
        provider=cfg.llm_provider, model=cfg.llm_model, api_key=cfg.openai_api_key
    )
    return ClipFinderService(
        subtitle_fetcher=YtdlpSubtitleFetcher(),
        agent=agent,
        chunk_minutes=cfg.clip_finder_chunk_minutes,
        overlap_minutes=cfg.clip_finder_overlap_minutes,
        max_candidates=cfg.clip_finder_max_candidates,
    )


def make_clip_repository(config: AppConfig | None = None):
    cfg = config or get_config()
    from cliptrans.adapters.persistence.clip_repository import SQLAlchemyClipRepository

    return SQLAlchemyClipRepository(cfg.database_url)
