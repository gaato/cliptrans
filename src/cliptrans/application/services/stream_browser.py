"""Stream browser service — wraps HolodexPort."""

from __future__ import annotations

from cliptrans.application.ports.holodex import HolodexPort
from cliptrans.domain.models import ChannelInfo, StreamInfo


class StreamBrowserService:
    def __init__(self, holodex: HolodexPort) -> None:
        self._holodex = holodex

    async def suggest_channels(self, query: str, *, limit: int = 10) -> list[ChannelInfo]:
        if not query or len(query) < 1:
            return []
        return await self._holodex.search_channels(query, limit=limit)

    async def list_live(self, *, org: str | None = None, limit: int = 50) -> list[StreamInfo]:
        return await self._holodex.list_live_streams(org=org, limit=limit)

    async def list_past(
        self,
        *,
        channel_id: str | None = None,
        org: str | None = None,
        limit: int = 50,
    ) -> list[StreamInfo]:
        return await self._holodex.list_past_streams(
            channel_id=channel_id, org=org, limit=limit
        )

    async def get_stream(self, video_id: str) -> StreamInfo:
        return await self._holodex.get_stream(video_id)
