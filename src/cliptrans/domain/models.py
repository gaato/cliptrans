from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from cliptrans.domain.enums import ASREngine, ClipStatus, ExportFormat, JobStatus, StageKind


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


# Clip finder domain models


class ChannelInfo(BaseModel):
    """Holodex から取得したチャンネル情報"""

    id: str
    name: str
    english_name: str | None = None
    photo: str | None = None
    org: str | None = None
    subscriber_count: int | None = None


class StreamInfo(BaseModel):
    """Holodex から取得した配信メタデータ"""

    video_id: str
    title: str
    channel_id: str
    channel_name: str
    channel_english_name: str | None = None
    channel_photo: str | None = None
    org: str | None = None
    duration: int = 0  # 秒
    status: str = "past"  # "live" | "upcoming" | "past"
    available_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    topic_id: str | None = None


class ChatDensity(BaseModel):
    """時間窓ごとのチャット密度"""

    start: float  # 秒
    end: float
    count: int
    intensity: float  # 全体平均に対する倍率


class ClipCandidate(BaseModel):
    """LLM が提案する切り抜き候補"""

    id: UUID = Field(default_factory=uuid4)
    stream_id: str
    start: float
    end: float
    title: str
    reason: str
    category: str  # "funny" | "emotional" | "collab" | "music" | "controversy"
    confidence: float
    chat_intensity: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClipSelection(BaseModel):
    """人間が確定した切り抜き区間"""

    id: UUID = Field(default_factory=uuid4)
    stream_id: str
    start: float
    end: float
    title: str
    notes: str = ""
    status: ClipStatus = ClipStatus.PENDING
    job_id: UUID | None = None
    candidate_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
