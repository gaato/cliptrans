from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageKind(StrEnum):
    INGEST = "ingest"
    PREPARE = "prepare"
    TRANSCRIBE = "transcribe"
    REGROUP = "regroup"
    TRANSLATE = "translate"
    EXPORT = "export"


class ASREngine(StrEnum):
    FASTER_WHISPER = "faster-whisper"
    WHISPERX = "whisperx"


class ExportFormat(StrEnum):
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    SRT_BILINGUAL = "srt-bilingual"
    KDENLIVE = "kdenlive"
    VTT_BILINGUAL = "vtt-bilingual"
    ASS_BILINGUAL = "ass-bilingual"
    PREVIEW_MP4 = "preview.mp4"
