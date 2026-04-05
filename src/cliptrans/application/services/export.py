"""ExportService — dispatch to the correct exporter for each requested format."""

from __future__ import annotations

from pathlib import Path

from cliptrans.adapters.exporters.ass import ASSExporter
from cliptrans.adapters.exporters.preview import PreviewExporter
from cliptrans.adapters.exporters.srt import SRTExporter
from cliptrans.adapters.exporters.vtt import VTTExporter
from cliptrans.domain.enums import ExportFormat
from cliptrans.domain.errors import ExportError
from cliptrans.domain.models import Job, Timeline


class ExportService:
    def __init__(self, bilingual: bool = False) -> None:
        self._bilingual = bilingual

    async def execute(
        self,
        job: Job,
        timeline: Timeline,
        *,
        video_path: Path | None = None,
    ) -> dict[ExportFormat, Path]:
        """Export all formats requested in job.config.

        Returns a mapping of ExportFormat → output file path.
        Failures for individual formats are collected and re-raised as a
        summary ExportError after attempting all formats.
        """
        assert job.data_dir is not None
        output_dir: Path = job.data_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        results: dict[ExportFormat, Path] = {}
        errors: list[str] = []

        for fmt in job.config.export_formats:
            try:
                path = await self._export_one(fmt, timeline, output_dir, video_path)
                results[fmt] = path
            except Exception as exc:
                errors.append(f"{fmt}: {exc}")

        if errors:
            raise ExportError("Some exports failed:\n" + "\n".join(errors))

        return results

    async def _export_one(
        self,
        fmt: ExportFormat,
        timeline: Timeline,
        output_dir: Path,
        video_path: Path | None,
    ) -> Path:
        match fmt:
            case ExportFormat.SRT:
                return await SRTExporter(bilingual=self._bilingual).export(
                    timeline, output_dir
                )
            case ExportFormat.SRT_BILINGUAL:
                return await SRTExporter(bilingual=True).export(
                    timeline, output_dir, filename="subtitles.bilingual.srt"
                )
            case ExportFormat.KDENLIVE:
                return await SRTExporter(bilingual=True).export(
                    timeline, output_dir, filename="subtitles.kdenlive.srt"
                )
            case ExportFormat.VTT:
                return await VTTExporter(bilingual=self._bilingual).export(
                    timeline, output_dir
                )
            case ExportFormat.VTT_BILINGUAL:
                return await VTTExporter(bilingual=True).export(
                    timeline, output_dir, filename="subtitles.bilingual.vtt"
                )
            case ExportFormat.ASS:
                return await ASSExporter(bilingual=self._bilingual).export(
                    timeline, output_dir
                )
            case ExportFormat.ASS_BILINGUAL:
                return await ASSExporter(bilingual=True).export(
                    timeline, output_dir, filename="subtitles.bilingual.ass"
                )
            case ExportFormat.PREVIEW_MP4:
                if video_path is None:
                    raise ExportError("video_path required for preview.mp4 export")
                return await PreviewExporter().export(timeline, output_dir, video_path)
            case _:
                raise ExportError(f"Unknown export format: {fmt}")
