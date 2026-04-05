"""TranscribeService — run ASR and store segments in timeline."""

from __future__ import annotations

from pathlib import Path

from cliptrans.application.ports.transcriber import TranscriberPort
from cliptrans.domain.models import ASRMeta, Job, Timeline
from cliptrans.timeline_io import write_timeline


class TranscribeService:
    def __init__(
        self,
        transcriber: TranscriberPort,
        asr_corrections: dict[str, str] | None = None,
    ) -> None:
        self._transcriber = transcriber
        self._asr_corrections: dict[str, str] = asr_corrections or {}

    async def execute(self, job: Job, timeline: Timeline, audio_path: Path) -> Timeline:
        """Transcribe *audio_path* and populate timeline.segments.

        Returns the updated timeline.
        """
        assert job.data_dir is not None
        cfg = job.config

        segments = await self._transcriber.transcribe(
            audio_path,
            language=cfg.source_language,
            model=cfg.asr_model,
        )

        # Apply post-ASR corrections (e.g. proper nouns the model mishears)
        if self._asr_corrections:
            for seg in segments:
                for wrong, correct in self._asr_corrections.items():
                    seg.text = seg.text.replace(wrong, correct)

        timeline.segments = segments
        timeline.asr = ASRMeta(
            engine=str(cfg.asr_engine),
            model=cfg.asr_model,
            language=cfg.source_language,
        )

        write_timeline(timeline, job.data_dir / "timeline.json")
        return timeline
