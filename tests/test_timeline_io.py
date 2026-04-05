"""Tests for timeline_io — read/write/validate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cliptrans.domain.errors import TimelineError
from cliptrans.domain.models import Timeline
from cliptrans.timeline_io import read_timeline, write_timeline


class TestWriteTimeline:
    def test_creates_file(self, tmp_path: Path, timeline: Timeline):
        path = tmp_path / "timeline.json"
        write_timeline(timeline, path)
        assert path.exists()

    def test_creates_parent_dirs(self, tmp_path: Path, timeline: Timeline):
        path = tmp_path / "nested" / "deep" / "timeline.json"
        write_timeline(timeline, path)
        assert path.exists()

    def test_valid_json(self, tmp_path: Path, timeline: Timeline):
        path = tmp_path / "timeline.json"
        write_timeline(timeline, path)
        data = json.loads(path.read_text())
        assert data["version"] == "1.0"
        assert "job_id" in data
        assert "segments" in data


class TestReadTimeline:
    def test_roundtrip(self, tmp_path: Path, timeline: Timeline):
        path = tmp_path / "timeline.json"
        write_timeline(timeline, path)
        restored = read_timeline(path)

        assert restored.job_id == timeline.job_id
        assert restored.version == timeline.version
        assert len(restored.segments) == len(timeline.segments)
        assert len(restored.utterances) == len(timeline.utterances)
        assert restored.utterances[0].translation == timeline.utterances[0].translation

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(TimelineError, match="Cannot read timeline"):
            read_timeline(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path: Path):
        bad = tmp_path / "timeline.json"
        bad.write_text("not json", encoding="utf-8")
        with pytest.raises(TimelineError, match="Cannot read timeline"):
            read_timeline(bad)

    def test_unsupported_version_raises(self, tmp_path: Path, timeline: Timeline):
        path = tmp_path / "timeline.json"
        data = json.loads(timeline.model_dump_json())
        data["version"] = "99.0"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(TimelineError, match="Unsupported timeline version"):
            read_timeline(path)

    def test_invalid_schema_raises(self, tmp_path: Path):
        path = tmp_path / "timeline.json"
        path.write_text(json.dumps({"version": "1.0", "job_id": "bad-uuid"}), encoding="utf-8")
        with pytest.raises(TimelineError, match="Invalid timeline schema"):
            read_timeline(path)
