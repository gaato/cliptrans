"""Live chat fetcher using yt-dlp to download replay chat JSON."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path


class YtdlpLiveChatFetcher:
    """Downloads YouTube live chat replay via yt-dlp and parses message timestamps."""

    async def fetch_events(self, video_id: str) -> list[dict]:
        """Return list of dicts with keys: ``offset_sec`` (float), ``message`` (str).

        Returns empty list if no live chat is available.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-sub",
                "--sub-lang",
                "live_chat",
                "--sub-format",
                "json",
                "--output",
                f"{tmpdir}/%(id)s.%(ext)s",
                url,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await proc.communicate()
            # yt-dlp exits 0 even when no live_chat available
            chat_files = list(Path(tmpdir).glob(f"{video_id}*.live_chat.json"))
            if not chat_files:
                return []
            return _parse_live_chat(chat_files[0])


def _parse_live_chat(path: Path) -> list[dict]:
    """Parse yt-dlp live_chat.json (newline-delimited JSON) into offset+message list."""
    events: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            replay = obj.get("replayChatItemAction", {})
            offset_ms = replay.get("videoOffsetTimeMsec")
            if offset_ms is None:
                continue
            offset_sec = int(offset_ms) / 1000.0
            for action in replay.get("actions", []):
                item = action.get("addChatItemAction", {}).get("item", {})
                renderer = item.get("liveChatTextMessageRenderer") or item.get(
                    "liveChatPaidMessageRenderer"
                )
                if renderer is None:
                    continue
                text = "".join(
                    run.get("text", "") for run in renderer.get("message", {}).get("runs", [])
                )
                events.append({"offset_sec": offset_sec, "message": text})
    return events
