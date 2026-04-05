"""Port (Protocol) for Holodex API access."""

from __future__ import annotations

from typing import Protocol

from cliptrans.domain.models import ChannelInfo, StreamInfo


class HolodexPort(Protocol):
    async def search_channels(
        self, query: str, *, limit: int = 10
    ) -> list[ChannelInfo]: ...

    async def list_live_streams(
        self, *, org: str | None = None, limit: int = 50
    ) -> list[StreamInfo]: ...

    async def list_past_streams(
        self, *, channel_id: str | None = None, org: str | None = None, limit: int = 50
    ) -> list[StreamInfo]: ...

    async def get_stream(self, video_id: str) -> StreamInfo: ...
