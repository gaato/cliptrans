"""HTML page routes (server-side rendered with Jinja2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from cliptrans.entrypoints.api.deps import (
    ClipFinder,
    ClipManager,
    ClipRepo,
    StreamBrowser,
    SubtitleFetcher,
)
from cliptrans.entrypoints.api.i18n import preferred_language

router = APIRouter()

_templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    browser: StreamBrowser,
    channel_id: str | None = None,
    channel_name: str = "",
    org: str | None = None,
    status: str = "past",
):
    try:
        if status == "live":
            streams = await browser.list_live(org=org, limit=50)
        else:
            streams = await browser.list_past(channel_id=channel_id, org=org, limit=50)
    except Exception:
        streams = []
    return _templates.TemplateResponse(
        request=request,
        name="streams.html",
        context={
            "streams": streams,
            "channel_id": channel_id or "",
            "channel_name": channel_name,
            "org": org or "",
            "status": status,
        },
    )


@router.get("/stream/{video_id}", response_class=HTMLResponse)
async def stream_detail(request: Request, video_id: str, browser: StreamBrowser, repo: ClipRepo):
    try:
        stream = await browser.get_stream(video_id)
    except Exception as exc:
        stream = None
        error = str(exc)
    else:
        error = None
    candidates = await repo.get_candidates(video_id) if stream else []
    selections = await repo.get_selections(stream_id=video_id, status="pending") if stream else []
    return _templates.TemplateResponse(
        request=request,
        name="stream_detail.html",
        context={
            "stream": stream,
            "candidates": candidates,
            "selections": selections,
            "error": error,
            "video_id": video_id,
        },
    )


@router.get("/selections", response_class=HTMLResponse)
async def selections_page(request: Request, manager: ClipManager):
    selections = await manager.list_selections(status="pending")
    return _templates.TemplateResponse(
        request=request, name="selections.html", context={"selections": selections}
    )


@router.post("/htmx/clips/find", response_class=HTMLResponse)
async def find_candidates_html(
    request: Request,
    finder: ClipFinder,
    repo: ClipRepo,
    video_id: Annotated[str, Form()],
    replace: Annotated[bool, Form()] = True,
):
    try:
        if replace:
            await repo.delete_candidates(video_id)
        candidates = await finder.find_candidates(
            video_id, output_language=preferred_language(request)
        )
        await repo.save_candidates(candidates)
    except Exception as exc:
        import traceback

        error_msg = str(exc) or traceback.format_exc().splitlines()[-1]
        return HTMLResponse(
            f'<p class="empty-message" style="color:var(--red)">Error: {error_msg}</p>',
            status_code=500,
        )
    return _templates.TemplateResponse(
        request=request,
        name="_candidates_fragment.html",
        context={"candidates": candidates, "video_id": video_id},
    )


@router.get("/sse/clips/find/{video_id}")
async def find_candidates_sse(
    request: Request,
    video_id: str,
    finder: ClipFinder,
    repo: ClipRepo,
    replace: bool = True,
):
    async def event_stream():
        if replace:
            await repo.delete_candidates(video_id)
        async for event in finder.find_candidates_stream(
            video_id, output_language=preferred_language(request)
        ):
            if await request.is_disconnected():
                break
            if event["type"] == "done":
                # Save to DB, then render the HTML fragment
                from cliptrans.domain.models import ClipCandidate

                candidates = [ClipCandidate(**c) for c in event["candidates"]]
                await repo.save_candidates(candidates)
                html = _templates.get_template("_candidates_fragment.html").render(
                    candidates=candidates, video_id=video_id
                )
                yield f"event: done\ndata: {json.dumps({'html': html})}\n\n"
            else:
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT into list of {start, end, start_sec, text} dicts."""
    import re

    block_re = re.compile(
        r"\d+\r?\n"
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n"
        r"((?:.*\r?\n)*?)"
        r"\r?\n",
        re.MULTILINE,
    )

    def ts_to_sec(ts: str) -> float:
        h, m, s_ms = ts.split(":")
        s, ms = s_ms.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    lines = []
    for m in block_re.finditer(srt_text + "\n"):
        start_ts, end_ts = m.group(1), m.group(2)
        text = m.group(3).strip().replace("\n", " ")
        if text:
            lines.append(
                {
                    "start": start_ts[:8],  # HH:MM:SS
                    "end": end_ts[:8],
                    "start_sec": ts_to_sec(start_ts),
                    "text": text,
                }
            )
    return lines


@router.get("/htmx/transcript/{video_id}", response_class=HTMLResponse)
async def transcript_html(
    request: Request,
    video_id: str,
    fetcher: SubtitleFetcher,
    start: float | None = None,
    end: float | None = None,
):
    try:
        srt_text = await fetcher.fetch_srt(video_id)
        lines = _parse_srt(srt_text)
        if start is not None:
            lines = [line for line in lines if line["start_sec"] >= start]
        if end is not None:
            lines = [line for line in lines if line["start_sec"] < end]
    except Exception as exc:
        return HTMLResponse(
            f'<p class="empty-message" style="color:var(--red)">Error: {exc}</p>',
            status_code=500,
        )
    return _templates.TemplateResponse(
        request=request,
        name="_transcript_fragment.html",
        context={"lines": lines, "video_id": video_id},
    )
