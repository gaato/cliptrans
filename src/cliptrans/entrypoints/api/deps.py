"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from cliptrans.adapters.holodex import HolodexAdapter
from cliptrans.adapters.persistence.clip_repository import SQLAlchemyClipRepository
from cliptrans.application.ports.subtitle_fetcher import SubtitleFetcherPort
from cliptrans.application.services.clip_finder import ClipFinderService
from cliptrans.application.services.clip_manager import ClipManagerService
from cliptrans.application.services.stream_browser import StreamBrowserService
from cliptrans.config import AppConfig, get_config


def _cfg() -> AppConfig:
    return get_config()


Config = Annotated[AppConfig, Depends(_cfg)]


def _stream_browser(cfg: Config) -> StreamBrowserService:
    from cliptrans.application.services.stream_browser import StreamBrowserService as SBS

    if not cfg.holodex_api_key:
        from cliptrans.adapters.holodex import _StubHolodex
        return SBS(_StubHolodex())
    return SBS(HolodexAdapter(cfg.holodex_api_key))


def _clip_repo(cfg: Config) -> SQLAlchemyClipRepository:
    return SQLAlchemyClipRepository(cfg.database_url)


def _clip_manager(
    repo: Annotated[SQLAlchemyClipRepository, Depends(_clip_repo)],
) -> ClipManagerService:
    return ClipManagerService(repo)


StreamBrowser = Annotated[StreamBrowserService, Depends(_stream_browser)]
ClipRepo = Annotated[SQLAlchemyClipRepository, Depends(_clip_repo)]
ClipManager = Annotated[ClipManagerService, Depends(_clip_manager)]


def _clip_finder(cfg: Config) -> ClipFinderService:
    from cliptrans.adapters.live_chat_fetcher import YtdlpLiveChatFetcher
    from cliptrans.adapters.llm.clip_finder_agent import ClipFinderAgent
    from cliptrans.adapters.subtitle_fetcher import YtdlpSubtitleFetcher

    agent = ClipFinderAgent(
        provider=cfg.llm_provider,
        model=cfg.llm_model,
        api_key=cfg.openai_api_key or cfg.anthropic_api_key or cfg.gemini_api_key,
    )
    return ClipFinderService(
        subtitle_fetcher=YtdlpSubtitleFetcher(),
        agent=agent,
        live_chat_fetcher=YtdlpLiveChatFetcher(),
        chunk_minutes=cfg.clip_finder_chunk_minutes,
        overlap_minutes=cfg.clip_finder_overlap_minutes,
        max_candidates=cfg.clip_finder_max_candidates,
    )


ClipFinder = Annotated[ClipFinderService, Depends(_clip_finder)]


def _subtitle_fetcher():
    from cliptrans.adapters.subtitle_fetcher import YtdlpSubtitleFetcher
    return YtdlpSubtitleFetcher()


SubtitleFetcher = Annotated[SubtitleFetcherPort, Depends(_subtitle_fetcher)]
