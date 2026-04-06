"""yt-dlp adapter implementing DownloaderPort."""

from __future__ import annotations

import asyncio
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

from cliptrans.domain.errors import IngestError
from cliptrans.domain.models import SourceMeta


class YtdlpDownloader:
    """Download video/audio from URL using yt-dlp subprocess."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def download(
        self,
        url: str,
        output_dir: Path,
        *,
        start: float | None = None,
        end: float | None = None,
    ) -> tuple[Path, SourceMeta]:
        output_dir.mkdir(parents=True, exist_ok=True)

        output_template = str(output_dir / "video.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--format",
            "bestvideo+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "--output",
            output_template,
            "--print-json",
        ]

        if start is not None or end is not None:
            section = _build_section(start, end)
            cmd += ["--download-sections", section, "--force-keyframes-at-cuts"]

        cmd.append(url)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise IngestError(
                f"yt-dlp failed (exit {proc.returncode}): {stderr.decode(errors='replace')}"
            )

        import json

        # yt-dlp --print-json may emit multiple JSON lines (one per format attempt);
        # the last non-empty line is the final merged info.
        info: dict = {}
        for line in stdout.decode(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("{"):
                info = json.loads(line)

        video_path = _locate_video(output_dir)
        meta = SourceMeta(
            url=url,
            title=info.get("title", ""),
            channel=info.get("channel") or info.get("uploader", ""),
            duration=float(info.get("duration", 0)),
            start_time=start,
            end_time=end,
        )
        return video_path, meta


def _build_section(start: float | None, end: float | None) -> str:
    """Build a yt-dlp --download-sections value like '*start-end'."""
    s = _fmt_time(start) if start is not None else "0"
    e = _fmt_time(end) if end is not None else "inf"
    return f"*{s}-{e}"


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _locate_video(output_dir: Path) -> Path:
    """Return the first video file produced in output_dir."""
    for ext in ("mp4", "mkv", "webm"):
        candidates = list(output_dir.glob(f"video.{ext}"))
        if candidates:
            return candidates[0]
    raise IngestError(f"No output video found in {output_dir}")
