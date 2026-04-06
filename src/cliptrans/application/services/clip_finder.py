"""Clip finder service — orchestrates subtitle fetch + chunk + LLM."""

from __future__ import annotations

from cliptrans.application.ports.subtitle_fetcher import SubtitleFetcherPort
from cliptrans.domain.models import ChatDensity, ClipCandidate


def _chunk_srt(
    srt_text: str, chunk_seconds: float, overlap_seconds: float
) -> list[tuple[float, str]]:
    """Split SRT into chunks of ~chunk_seconds with overlap. Returns (offset, chunk_srt) pairs."""
    import re

    block_pattern = re.compile(
        r"(\d+)\r?\n"
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n"
        r"((?:.*\r?\n)*?)"
        r"\r?\n",
        re.MULTILINE,
    )

    def ts_to_sec(ts: str) -> float:
        h, m, s_ms = ts.split(":")
        s, ms = s_ms.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    blocks = [(ts_to_sec(m.group(2)), m.group(0)) for m in block_pattern.finditer(srt_text + "\n")]
    if not blocks:
        return []

    def sec_to_srt_ts(sec: float) -> str:
        sec = max(0.0, sec)
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    total_duration = blocks[-1][0]
    chunks: list[tuple[float, str]] = []
    start = 0.0
    while start < total_duration:
        end = start + chunk_seconds
        chunk_start = max(0.0, start - overlap_seconds)
        window_blocks = [(ts, b) for ts, b in blocks if chunk_start <= ts < end]
        if window_blocks:
            # Renumber blocks and rewrite timestamps to be relative to chunk_start
            renumbered = []
            for idx, (_ts, b) in enumerate(window_blocks, 1):
                b = re.sub(r"^\d+", str(idx), b, count=1)

                # Rewrite timestamps: HH:MM:SS,mmm --> HH:MM:SS,mmm (relative)
                def _shift_ts(m_ts: re.Match, *, _chunk_start: float = chunk_start) -> str:
                    t1 = ts_to_sec(m_ts.group(1)) - _chunk_start
                    t2 = ts_to_sec(m_ts.group(2)) - _chunk_start
                    return f"{sec_to_srt_ts(t1)} --> {sec_to_srt_ts(t2)}"

                b = re.sub(
                    r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
                    _shift_ts,
                    b,
                )
                renumbered.append(b)
            chunks.append((chunk_start, "".join(renumbered)))
        start = end
    return chunks


def _chat_intensity_for(chat_density: list[ChatDensity], start: float, end: float) -> float | None:
    """Average chat intensity over [start, end] seconds."""
    if not chat_density:
        return None
    bins = [d for d in chat_density if d.end > start and d.start < end]
    if not bins:
        return None
    return sum(b.intensity for b in bins) / len(bins)


class ClipFinderService:
    def __init__(
        self,
        subtitle_fetcher: SubtitleFetcherPort,
        agent,  # ClipFinderAgent — avoid import cycle
        live_chat_fetcher=None,  # YtdlpLiveChatFetcher — optional
        chunk_minutes: float = 10.0,
        overlap_minutes: float = 1.0,
        max_candidates: int = 20,
    ) -> None:
        self._fetcher = subtitle_fetcher
        self._agent = agent
        self._live_chat_fetcher = live_chat_fetcher
        self._chunk_seconds = chunk_minutes * 60
        self._overlap_seconds = overlap_minutes * 60
        self._max_candidates = max_candidates

    async def find_candidates(self, video_id: str) -> list[ClipCandidate]:
        import asyncio

        from cliptrans.application.services.chat_analyzer import ChatAnalyzerService

        # Fetch subtitles and live chat concurrently
        subtitle_task = asyncio.create_task(self._fetcher.fetch_srt(video_id))

        live_chat_task: asyncio.Task | None = None
        if self._live_chat_fetcher is not None:
            live_chat_task = asyncio.create_task(self._live_chat_fetcher.fetch_events(video_id))

        srt_text = await subtitle_task

        chat_density: list[ChatDensity] = []
        if live_chat_task is not None:
            live_chat_events = await live_chat_task
            if live_chat_events:
                # Estimate duration from last subtitle timestamp
                chunks_tmp = _chunk_srt(srt_text, self._chunk_seconds, self._overlap_seconds)
                stream_duration = (
                    int(chunks_tmp[-1][0] + self._chunk_seconds) if chunks_tmp else 3600
                )
                analyzer = ChatAnalyzerService()
                chat_density = analyzer.compute_from_live_chat(
                    live_chat_events,
                    duration=stream_duration,
                    window_seconds=60.0,
                )

        if not srt_text.strip():
            return []

        chunks = _chunk_srt(srt_text, self._chunk_seconds, self._overlap_seconds)
        all_candidates: list[ClipCandidate] = []
        for offset, chunk in chunks:
            candidates = await self._agent.find_candidates(video_id, chunk, chunk_offset=offset)
            all_candidates.extend(candidates)

        # Attach chat intensity and sort by combined score
        for c in all_candidates:
            c.chat_intensity = _chat_intensity_for(chat_density, c.start, c.end)

        def _score(c: ClipCandidate) -> float:
            base = c.confidence
            if c.chat_intensity is not None:
                base += min(c.chat_intensity * 0.1, 0.15)
            return base

        all_candidates.sort(key=_score, reverse=True)
        return all_candidates[: self._max_candidates]

    async def find_candidates_stream(self, video_id: str):
        """Async generator yielding SSE-style dicts during processing.

        Yields dicts with keys:
          {"type": "progress", "step": int, "total": int, "message": str}
          {"type": "done", "candidates": [...serialized...]}
          {"type": "error", "message": str}
        """
        import asyncio

        from cliptrans.application.services.chat_analyzer import ChatAnalyzerService

        try:
            yield {"type": "progress", "step": 0, "total": 1, "message": "字幕とチャットを取得中…"}

            subtitle_task = asyncio.create_task(self._fetcher.fetch_srt(video_id))
            live_chat_task = (
                asyncio.create_task(self._live_chat_fetcher.fetch_events(video_id))
                if self._live_chat_fetcher is not None
                else None
            )

            srt_text = await subtitle_task

            chat_density: list[ChatDensity] = []
            if live_chat_task is not None:
                live_chat_events = await live_chat_task
                if live_chat_events:
                    chunks_tmp = _chunk_srt(srt_text, self._chunk_seconds, self._overlap_seconds)
                    stream_duration = (
                        int(chunks_tmp[-1][0] + self._chunk_seconds) if chunks_tmp else 3600
                    )
                    analyzer = ChatAnalyzerService()
                    chat_density = analyzer.compute_from_live_chat(
                        live_chat_events, duration=stream_duration, window_seconds=60.0
                    )

            if not srt_text.strip():
                yield {"type": "error_event", "message": "字幕データが見つかりませんでした。"}
                return

            chunks = _chunk_srt(srt_text, self._chunk_seconds, self._overlap_seconds)
            total = len(chunks)
            all_candidates: list[ClipCandidate] = []

            for i, (offset, chunk) in enumerate(chunks, 1):
                start_min = int(offset // 60)
                yield {
                    "type": "progress",
                    "step": i,
                    "total": total,
                    "message": f"チャンク {i}/{total} を解析中… ({start_min}分〜)",
                }
                candidates = await self._agent.find_candidates(video_id, chunk, chunk_offset=offset)
                all_candidates.extend(candidates)

            for c in all_candidates:
                c.chat_intensity = _chat_intensity_for(chat_density, c.start, c.end)

            def _score(c: ClipCandidate) -> float:
                base = c.confidence
                if c.chat_intensity is not None:
                    base += min(c.chat_intensity * 0.1, 0.15)
                return base

            all_candidates.sort(key=_score, reverse=True)
            result = all_candidates[: self._max_candidates]
            yield {"type": "done", "candidates": [c.model_dump(mode="json") for c in result]}
        except Exception as exc:
            yield {"type": "error_event", "message": str(exc)}
