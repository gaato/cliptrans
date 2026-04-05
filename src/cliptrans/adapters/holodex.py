"""Holodex API adapter using httpx."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from cliptrans.domain.errors import HolodexError
from cliptrans.domain.models import ChannelInfo, StreamInfo

_BASE_URL = "https://holodex.net/api/v2"


class HolodexAdapter:
    def __init__(self, api_key: str) -> None:
        self._headers = {"X-APIKEY": api_key}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=_BASE_URL, headers=self._headers, timeout=30.0)

    @staticmethod
    def _parse_available_at(data: dict) -> datetime:
        raw = data.get("available_at") or data.get("published_at")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime(1970, 1, 1, tzinfo=UTC)

    def _parse_stream(self, data: dict) -> StreamInfo:
        ch = data.get("channel", {})
        return StreamInfo(
            video_id=data["id"],
            title=data.get("title", ""),
            channel_id=data.get("channel_id", ch.get("id", "")),
            channel_name=ch.get("name", data.get("channel_id", "")),
            channel_english_name=ch.get("english_name"),
            channel_photo=ch.get("photo"),
            org=ch.get("org") or data.get("org"),
            duration=data.get("duration", 0),
            status=data.get("status", "past"),
            available_at=self._parse_available_at(data),
            topic_id=data.get("topic_id"),
        )

    async def search_channels(
        self, query: str, *, limit: int = 10
    ) -> list[ChannelInfo]:
        """Search channels via autoComplete, then fetch their details."""
        try:
            async with self._client() as client:
                ac_resp = await client.get(
                    "/search/autoComplete", params={"q": query}
                )
                ac_resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HolodexError(f"Holodex autoComplete failed: {exc}") from exc

        channel_ids = [
            item["value"]
            for item in ac_resp.json()
            if item.get("type") == "channel"
        ][:limit]
        if not channel_ids:
            return []

        async def _fetch_one(cid: str) -> ChannelInfo | None:
            try:
                async with self._client() as client:
                    r = await client.get(f"/channels/{cid}")
                    r.raise_for_status()
                    ch = r.json()
                    return ChannelInfo(
                        id=ch["id"],
                        name=ch.get("name", ""),
                        english_name=ch.get("english_name"),
                        photo=ch.get("photo"),
                        org=ch.get("org"),
                        subscriber_count=ch.get("subscriber_count"),
                    )
            except Exception:
                return None

        import asyncio

        results = await asyncio.gather(*[_fetch_one(cid) for cid in channel_ids])
        return [r for r in results if r is not None]

    async def list_live_streams(
        self, *, org: str | None = None, limit: int = 50
    ) -> list[StreamInfo]:
        params: dict = {"status": "live", "limit": limit, "type": "stream"}
        if org:
            params["org"] = org
        try:
            async with self._client() as client:
                resp = await client.get("/live", params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HolodexError(f"Holodex /live failed: {exc}") from exc
        return [self._parse_stream(item) for item in resp.json()]

    async def list_past_streams(
        self, *, channel_id: str | None = None, org: str | None = None, limit: int = 50
    ) -> list[StreamInfo]:
        params: dict = {"status": "past", "limit": limit, "type": "stream"}
        if org:
            params["org"] = org
        if channel_id:
            params["channel_id"] = channel_id
        try:
            async with self._client() as client:
                resp = await client.get("/videos", params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HolodexError(f"Holodex /videos failed: {exc}") from exc
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", [])
        return [self._parse_stream(item) for item in items]

    async def get_stream(self, video_id: str) -> StreamInfo:
        try:
            async with self._client() as client:
                resp = await client.get(f"/videos/{video_id}")
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HolodexError(f"Holodex /videos/{video_id} failed: {exc}") from exc
        return self._parse_stream(resp.json())

class _StubHolodex:
    """No-op Holodex adapter used when no API key is configured."""

    async def search_channels(self, query: str, *, limit: int = 10) -> list:
        return []

    async def list_live_streams(self, *, org=None, limit=50):
        return []

    async def list_past_streams(self, *, channel_id=None, org=None, limit=50):
        return []

    async def get_stream(self, video_id: str):
        from cliptrans.domain.errors import HolodexError

        raise HolodexError("CLIPTRANS_HOLODEX_API_KEY is not set")
