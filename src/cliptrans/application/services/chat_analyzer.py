"""Chat density analyzer — computes chat intensity from yt-dlp live chat events."""

from __future__ import annotations

from collections import defaultdict

from cliptrans.domain.models import ChatDensity


class ChatAnalyzerService:
    """Compute per-window chat density from yt-dlp live chat replay events."""

    def compute_from_live_chat(
        self,
        events: list[dict],
        duration: int,
        window_seconds: float = 60.0,
    ) -> list[ChatDensity]:
        """Compute density from yt-dlp live chat events (each has ``offset_sec`` key)."""
        if duration <= 0 or not events:
            return []

        bucket: defaultdict[int, int] = defaultdict(int)
        for ev in events:
            ts = ev.get("offset_sec")
            if ts is None or ts < 0 or ts > duration:
                continue
            key = int(ts // window_seconds)
            bucket[key] += 1

        return self._buckets_to_density(bucket, duration, window_seconds)

    def _buckets_to_density(
        self,
        bucket: defaultdict[int, int],
        duration: int,
        window_seconds: float,
    ) -> list[ChatDensity]:
        if not bucket:
            return []

        mean_count = sum(bucket.values()) / len(bucket)

        result: list[ChatDensity] = []
        num_windows = int(duration // window_seconds) + 1
        for i in range(num_windows):
            start = i * window_seconds
            end = min((i + 1) * window_seconds, duration)
            count = bucket[i]
            intensity = count / mean_count if mean_count > 0 else 0.0
            result.append(ChatDensity(start=start, end=end, count=count, intensity=intensity))
        return result
