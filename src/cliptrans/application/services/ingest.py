"""IngestService — download source video and record SourceMeta."""

from __future__ import annotations

from pathlib import Path

from cliptrans.application.ports.downloader import DownloaderPort
from cliptrans.domain.models import Job, SourceMeta, Timeline
from cliptrans.timeline_io import write_timeline


class IngestService:
    def __init__(self, downloader: DownloaderPort) -> None:
        self._downloader = downloader

    async def execute(self, job: Job, timeline: Timeline) -> tuple[Path, SourceMeta]:
        """Download the source video for *job* and update *timeline*.

        Returns (video_path, source_meta).  The caller is responsible for
        persisting Job / Timeline state.
        """
        assert job.data_dir is not None, "job.data_dir must be set before ingest"
        output_dir: Path = job.data_dir

        video_path, meta = await self._downloader.download(
            job.config.source_url,
            output_dir,
            start=job.config.start_time,
            end=job.config.end_time,
        )

        timeline.source = meta
        write_timeline(timeline, output_dir / "timeline.json")

        return video_path, meta
