"""WebVTT subtitle exporter."""

from __future__ import annotations

from pathlib import Path

from cliptrans.adapters.exporters._utils import format_vtt_timestamp
from cliptrans.domain.models import Timeline


class VTTExporter:
    def __init__(self, bilingual: bool = False) -> None:
        self._bilingual = bilingual

    async def export(
        self, timeline: Timeline, output_dir: Path, *, filename: str = "subtitles.vtt"
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        lines: list[str] = ["WEBVTT", ""]

        for utt in timeline.utterances:
            start = format_vtt_timestamp(utt.start)
            end = format_vtt_timestamp(utt.end)
            text = utt.translation or utt.original
            lines.append(f"{start} --> {end}")
            if self._bilingual and utt.translation:
                lines.append(utt.original)
            lines.append(text)
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
