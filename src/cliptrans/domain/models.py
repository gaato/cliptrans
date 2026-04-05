from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from cliptrans.domain.enums import ASREngine, ExportFormat, JobStatus, StageKind


class Word(BaseModel):
    start: float
    end: float
    word: str
    confidence: float | None = None


class Segment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    start: float
    end: float
    text: str
    speaker: str | None = None
    confidence: float | None = None
    language: str
    words: list[Word] | None = None


class Utterance(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    segment_ids: list[UUID]
    start: float
    end: float
    original: str
    translation: str | None = None
    speaker: str | None = None


class SourceMeta(BaseModel):
    url: str
    title: str
    channel: str
    duration: float
    start_time: float | None = None
    end_time: float | None = None


class MediaInfo(BaseModel):
    duration: float
    width: int | None = None
    height: int | None = None
    audio_sample_rate: int | None = None
    audio_channels: int | None = None


class ASRMeta(BaseModel):
    engine: str
    model: str
    language: str


class TranslationMeta(BaseModel):
    provider: str
    model: str
    source_language: str
    target_language: str
    glossary: dict[str, str] = {}


class Timeline(BaseModel):
    version: str = "1.0"
    job_id: UUID
    source: SourceMeta
    asr: ASRMeta | None = None
    segments: list[Segment] = []
    utterances: list[Utterance] = []
    translation: TranslationMeta | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobConfig(BaseModel):
    source_url: str
    start_time: float | None = None
    end_time: float | None = None
    source_language: str = "ja"
    target_language: str = "en"
    asr_engine: ASREngine = ASREngine.FASTER_WHISPER
    asr_model: str = "large-v3"
    enable_diarization: bool = False
    export_formats: list[ExportFormat] = [ExportFormat.SRT]


class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    config: JobConfig
    status: JobStatus = JobStatus.PENDING
    current_stage: StageKind | None = None
    completed_stages: list[StageKind] = []
    error: str | None = None
    data_dir: Path | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
