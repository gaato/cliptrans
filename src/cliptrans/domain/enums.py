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


class ClipStatus(StrEnum):
    PENDING = "pending"       # 候補として表示中
    QUEUED = "queued"         # 制作キュー投入済み
    PROCESSING = "processing" # パイプライン実行中
    DONE = "done"             # 完了
    REJECTED = "rejected"     # 人間が却下
