"""Stream listing and detail API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from cliptrans.domain.models import ChannelInfo, StreamInfo
from cliptrans.entrypoints.api.deps import StreamBrowser

router = APIRouter()


@router.get("/channels/suggest", response_model=list[ChannelInfo])
async def suggest_channels(
    browser: StreamBrowser,
    q: str = Query("", min_length=1),
    limit: int = Query(8, ge=1, le=20),
):
    return await browser.suggest_channels(q, limit=limit)


@router.get("", response_model=list[StreamInfo])
async def list_streams(
    browser: StreamBrowser,
    status: str = Query("past", pattern="^(live|past)$"),
    channel_id: str | None = Query(None),
    org: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    if status == "live":
        return await browser.list_live(org=org, limit=limit)
    return await browser.list_past(channel_id=channel_id, org=org, limit=limit)


@router.get("/{video_id}", response_model=StreamInfo)
async def get_stream(video_id: str, browser: StreamBrowser):
    try:
        return await browser.get_stream(video_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
