"""Tests for SRT / VTT / ASS exporters."""

from __future__ import annotations

from pathlib import Path

from cliptrans.adapters.exporters._utils import format_srt_timestamp, format_vtt_timestamp
from cliptrans.adapters.exporters.ass import ASSExporter
from cliptrans.adapters.exporters.srt import SRTExporter
from cliptrans.adapters.exporters.vtt import VTTExporter
from cliptrans.application.services.export import ExportService
from cliptrans.domain.enums import ExportFormat
from cliptrans.domain.models import Timeline

# ── Timestamp helpers ─────────────────────────────────────────────────────────


class TestTimestampFormatters:
    def test_srt_zero(self):
        assert format_srt_timestamp(0.0) == "00:00:00,000"

    def test_srt_one_hour(self):
        assert format_srt_timestamp(3600.0) == "01:00:00,000"

    def test_srt_with_millis(self):
        assert format_srt_timestamp(1.5) == "00:00:01,500"

    def test_srt_complex(self):
        assert format_srt_timestamp(3723.456) == "01:02:03,456"

    def test_vtt_zero(self):
        assert format_vtt_timestamp(0.0) == "00:00:00.000"

    def test_vtt_separator_is_dot(self):
        result = format_vtt_timestamp(1.5)
        assert "." in result
        assert "," not in result


# ── SRT ───────────────────────────────────────────────────────────────────────


class TestSRTExporter:
    async def test_creates_file(self, tmp_path: Path, timeline: Timeline):
        path = await SRTExporter().export(timeline, tmp_path)
        assert path.exists()
        assert path.suffix == ".srt"

    async def test_index_starts_at_1(self, tmp_path: Path, timeline: Timeline):
        path = await SRTExporter().export(timeline, tmp_path)
        lines = path.read_text().splitlines()
        assert lines[0] == "1"

    async def test_arrow_present(self, tmp_path: Path, timeline: Timeline):
        path = await SRTExporter().export(timeline, tmp_path)
        assert " --> " in path.read_text()

    async def test_uses_translation_when_available(self, tmp_path: Path, timeline: Timeline):
        path = await SRTExporter().export(timeline, tmp_path)
        content = path.read_text()
        # English translations from fixture should appear
        assert "Hello, everyone." in content

    async def test_falls_back_to_original(self, tmp_path: Path, timeline: Timeline):
        # Strip translations
        for utt in timeline.utterances:
            utt.translation = None
        path = await SRTExporter().export(timeline, tmp_path)
        content = path.read_text()
        assert "こんにちは" in content

    async def test_bilingual_includes_original(self, tmp_path: Path, timeline: Timeline):
        path = await SRTExporter(bilingual=True).export(timeline, tmp_path)
        content = path.read_text()
        assert "こんにちは" in content
        assert "Hello" in content

    async def test_entry_count_matches_utterances(self, tmp_path: Path, timeline: Timeline):
        path = await SRTExporter().export(timeline, tmp_path)
        # Count index lines (lines that are bare integers)
        lines = path.read_text().splitlines()
        indices = [x for x in lines if x.strip().isdigit()]
        assert len(indices) == len(timeline.utterances)


class TestExportService:
    async def test_kdenlive_exports_bilingual_srt(self, job, timeline: Timeline):
        job.config.export_formats = [ExportFormat.KDENLIVE]

        results = await ExportService().execute(job, timeline)

        path = results[ExportFormat.KDENLIVE]
        assert path.name == "subtitles.kdenlive.srt"
        content = path.read_text()
        assert "こんにちは" in content
        assert "Hello, everyone." in content


# ── VTT ───────────────────────────────────────────────────────────────────────


class TestVTTExporter:
    async def test_starts_with_webvtt(self, tmp_path: Path, timeline: Timeline):
        path = await VTTExporter().export(timeline, tmp_path)
        assert path.read_text().startswith("WEBVTT")

    async def test_creates_vtt_file(self, tmp_path: Path, timeline: Timeline):
        path = await VTTExporter().export(timeline, tmp_path)
        assert path.suffix == ".vtt"

    async def test_uses_dot_separator(self, tmp_path: Path, timeline: Timeline):
        path = await VTTExporter().export(timeline, tmp_path)
        # VTT uses "." not "," for milliseconds
        lines = [x for x in path.read_text().splitlines() if "-->" in x]
        for line in lines:
            assert "," not in line


# ── ASS ───────────────────────────────────────────────────────────────────────


class TestASSExporter:
    async def test_creates_ass_file(self, tmp_path: Path, timeline: Timeline):
        path = await ASSExporter().export(timeline, tmp_path)
        assert path.suffix == ".ass"

    async def test_has_script_info_header(self, tmp_path: Path, timeline: Timeline):
        path = await ASSExporter().export(timeline, tmp_path)
        assert "[Script Info]" in path.read_text()

    async def test_has_events_section(self, tmp_path: Path, timeline: Timeline):
        path = await ASSExporter().export(timeline, tmp_path)
        assert "[Events]" in path.read_text()

    async def test_dialogue_lines(self, tmp_path: Path, timeline: Timeline):
        path = await ASSExporter().export(timeline, tmp_path)
        dialogue_lines = [x for x in path.read_text().splitlines() if x.startswith("Dialogue:")]
        assert len(dialogue_lines) == len(timeline.utterances)

    async def test_bilingual_doubles_dialogue(self, tmp_path: Path, timeline: Timeline):
        path = await ASSExporter(bilingual=True).export(timeline, tmp_path)
        dialogue_lines = [x for x in path.read_text().splitlines() if x.startswith("Dialogue:")]
        # Each utterance → 2 lines (original + translation)
        assert len(dialogue_lines) == len(timeline.utterances) * 2
