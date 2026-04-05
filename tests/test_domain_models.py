"""Tests for domain models — validation, defaults, serialisation."""

from __future__ import annotations

from uuid import UUID

import pytest

from cliptrans.domain.enums import ASREngine, ExportFormat, JobStatus, StageKind
from cliptrans.domain.models import (
    Job,
    JobConfig,
    Segment,
    Timeline,
    Utterance,
    Word,
)


class TestSegment:
    def test_defaults(self):
        seg = Segment(start=0.0, end=1.0, text="hello", language="en")
        assert isinstance(seg.id, UUID)
        assert seg.speaker is None
        assert seg.words is None

    def test_with_words(self):
        w = Word(start=0.0, end=0.5, word="hello", confidence=0.9)
        seg = Segment(start=0.0, end=1.0, text="hello", language="en", words=[w])
        assert seg.words is not None
        assert seg.words[0].word == "hello"

    def test_serialise_roundtrip(self):
        seg = Segment(start=1.23, end=4.56, text="テスト", language="ja")
        restored = Segment.model_validate_json(seg.model_dump_json())
        assert restored.id == seg.id
        assert restored.text == seg.text


class TestUtterance:
    def test_defaults(self):
        utt = Utterance(segment_ids=[], start=0.0, end=1.0, original="test")
        assert utt.translation is None
        assert utt.speaker is None

    def test_copy_with_translation(self):
        utt = Utterance(segment_ids=[], start=0.0, end=1.0, original="hello")
        updated = utt.model_copy(update={"translation": "こんにちは"})
        assert updated.id == utt.id
        assert updated.translation == "こんにちは"
        assert utt.translation is None  # original unchanged


class TestJobConfig:
    def test_defaults(self):
        cfg = JobConfig(source_url="https://example.com/v?id=abc")
        assert cfg.source_language == "ja"
        assert cfg.target_language == "en"
        assert cfg.asr_engine == ASREngine.FASTER_WHISPER
        assert ExportFormat.SRT in cfg.export_formats

    def test_validation_error_without_url(self):
        with pytest.raises(Exception):
            JobConfig()  # type: ignore[call-arg]


class TestJob:
    def test_defaults(self, job_config):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        job = Job(config=job_config, created_at=now, updated_at=now)
        assert job.status == JobStatus.PENDING
        assert job.completed_stages == []
        assert job.current_stage is None
        assert job.error is None


class TestTimeline:
    def test_serialise_roundtrip(self, timeline: Timeline):
        json_str = timeline.model_dump_json()
        restored = Timeline.model_validate_json(json_str)
        assert restored.job_id == timeline.job_id
        assert len(restored.segments) == len(timeline.segments)
        assert len(restored.utterances) == len(timeline.utterances)
        assert restored.source.url == timeline.source.url

    def test_version_default(self, timeline: Timeline):
        assert timeline.version == "1.0"
