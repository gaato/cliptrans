"""Subtitle fetcher using yt-dlp to download auto-generated captions."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from cliptrans.domain.errors import SubtitleFetchError


class YtdlpSubtitleFetcher:
    """Downloads YouTube auto-captions via yt-dlp without downloading the video."""

    async def fetch_srt(self, video_id: str) -> str:
        """Fetch SRT subtitles. Auto-detects the best available caption language
        from the video's metadata (prefers native language, then English)."""
        import json as _json
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Get metadata to find the best available caption language
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--dump-json", "--skip-download", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        lang = ""  # will be set from metadata
        if stdout:
            try:
                info = _json.loads(stdout)
                native_lang = info.get("language") or ""
                available = list((info.get("automatic_captions") or {}).keys())
                if available:
                    native_in_avail = native_lang and native_lang in available
                    preferred = [native_lang if native_in_avail else None, "en", "en-orig"]
                    lang = next(
                        (
                            candidate
                            for candidate in preferred
                            if candidate and candidate in available
                        ),
                        available[0],
                    )
            except Exception:
                pass

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-sub",
                "--sub-lang", lang,
                "--sub-format", "srt",
                "--output", f"{tmpdir}/%(id)s.%(ext)s",
                url,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            srt_files = list(Path(tmpdir).glob(f"{video_id}*.srt"))
            if srt_files:
                return srt_files[0].read_text(encoding="utf-8")

            if proc.returncode != 0:
                raise SubtitleFetchError(
                    f"yt-dlp failed for {video_id}: {stderr.decode()[:500]}"
                )
            return ""
