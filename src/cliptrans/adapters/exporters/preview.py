"""Generate a preview.mp4 by burning ASS subtitles into the source video."""

from __future__ import annotations

import asyncio
from pathlib import Path

from cliptrans.domain.errors import ExportError
from cliptrans.domain.models import Timeline

from .ass import ASSExporter


class PreviewExporter:
    async def export(
        self,
        timeline: Timeline,
        output_dir: Path,
        video_path: Path,
    ) -> Path:
        """Burn subtitles from *timeline* into *video_path* → preview.mp4."""
        ass_path = await ASSExporter(bilingual=True).export(timeline, output_dir)
        preview_path = output_dir / "preview.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"ass={ass_path}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            str(preview_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ExportError(
                f"ffmpeg preview failed (exit {proc.returncode}): "
                f"{stderr.decode(errors='replace')}"
            )
        return preview_path
