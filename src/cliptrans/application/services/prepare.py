"""PrepareService — extract audio and optionally generate proxy."""

from __future__ import annotations

from pathlib import Path

from cliptrans.application.ports.media import MediaProcessorPort
from cliptrans.domain.models import Job, Timeline
from cliptrans.timeline_io import write_timeline


class PrepareService:
    def __init__(self, media_processor: MediaProcessorPort) -> None:
        self._media = media_processor

    async def execute(
        self,
        job: Job,
        timeline: Timeline,
        video_path: Path,
        *,
        make_proxy: bool = False,
    ) -> Path:
        """Extract audio from *video_path*.

        Returns the path to the extracted audio file (WAV).
        If *make_proxy* is True, also generates a low-res proxy.mp4.
        """
        assert job.data_dir is not None
        data_dir: Path = job.data_dir

        audio_path = data_dir / "audio.wav"
        audio_path = await self._media.extract_audio(video_path, audio_path)

        if make_proxy:
            proxy_path = data_dir / "proxy.mp4"
            await self._media.make_proxy(video_path, proxy_path)

        write_timeline(timeline, data_dir / "timeline.json")
        return audio_path
