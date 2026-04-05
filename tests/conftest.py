"""Shared pytest fixtures for cliptrans tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cliptrans.domain.enums import ASREngine, ExportFormat, JobStatus
from cliptrans.domain.models import (
    ASRMeta,
    Job,
    JobConfig,
    Segment,
    SourceMeta,
    Timeline,
    Utterance,
    Word,
)


@pytest.fixture()
def now() -> datetime:
    return datetime(2026, 4, 5, 12, 0, 0, tzinfo=UTC)


@pytest.fixture()
def source_meta() -> SourceMeta:
    return SourceMeta(
        url="https://www.youtube.com/watch?v=XXXXXXXXXXX",
        title="テスト配信",
        channel="テストチャンネル",
        duration=300.0,
        start_time=0.0,
        end_time=60.0,
    )


@pytest.fixture()
def segments() -> list[Segment]:
    return [
        Segment(
            start=0.0, end=2.0, text="こんにちは、", language="ja",
            words=[Word(start=0.0, end=2.0, word="こんにちは、", confidence=0.95)],
        ),
        Segment(
            start=2.1, end=4.5, text="みなさん。", language="ja",
        ),
        Segment(
            start=6.0, end=9.0, text="今日もよろしくお願いします。", language="ja",
        ),
        Segment(
            start=9.1, end=11.0, text="早速始めましょう！", language="ja",
        ),
    ]


@pytest.fixture()
def utterances(segments: list[Segment]) -> list[Utterance]:
    return [
        Utterance(
            segment_ids=[segments[0].id, segments[1].id],
            start=0.0, end=4.5,
            original="こんにちは、みなさん。",
            translation="Hello, everyone.",
        ),
        Utterance(
            segment_ids=[segments[2].id, segments[3].id],
            start=6.0, end=11.0,
            original="今日もよろしくお願いします。早速始めましょう！",
            translation="Thanks for joining today. Let's get started!",
        ),
    ]


@pytest.fixture()
def timeline(
    source_meta: SourceMeta,
    segments: list[Segment],
    utterances: list[Utterance],
    now: datetime,
) -> Timeline:
    return Timeline(
        job_id=uuid4(),
        source=source_meta,
        asr=ASRMeta(engine="faster-whisper", model="large-v3", language="ja"),
        segments=segments,
        utterances=utterances,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def job_config() -> JobConfig:
    return JobConfig(
        source_url="https://www.youtube.com/watch?v=XXXXXXXXXXX",
        start_time=0.0,
        end_time=60.0,
        source_language="ja",
        target_language="en",
        asr_engine=ASREngine.FASTER_WHISPER,
        asr_model="large-v3",
        export_formats=[ExportFormat.SRT, ExportFormat.VTT, ExportFormat.ASS],
    )


@pytest.fixture()
def job(job_config: JobConfig, now: datetime, tmp_path) -> Job:
    return Job(
        config=job_config,
        status=JobStatus.PENDING,
        data_dir=tmp_path,
        created_at=now,
        updated_at=now,
    )
