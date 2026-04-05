"""Port (Protocol) for subtitle fetching."""

from __future__ import annotations

from typing import Protocol


class SubtitleFetcherPort(Protocol):
    async def fetch_srt(self, video_id: str) -> str:
        """Fetch SRT subtitle for a YouTube video. Returns the SRT text content."""
        ...
