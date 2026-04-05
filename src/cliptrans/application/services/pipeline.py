"""PipelineOrchestrator — runs the full ingest→export pipeline for a Job.

Each stage is checkpointed to the DB so interrupted jobs can be resumed
with --resume.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from cliptrans.application.ports.downloader import DownloaderPort
from cliptrans.application.ports.media import MediaProcessorPort
from cliptrans.application.ports.repository import JobRepository
from cliptrans.application.ports.transcriber import TranscriberPort
from cliptrans.application.ports.translator import TranslatorPort
from cliptrans.application.services.export import ExportService
from cliptrans.application.services.ingest import IngestService
from cliptrans.application.services.prepare import PrepareService
from cliptrans.application.services.regroup import RegroupService
from cliptrans.application.services.transcribe import TranscribeService
from cliptrans.application.services.translate import TranslateService
from cliptrans.config import AppConfig
from cliptrans.domain.enums import JobStatus, StageKind
from cliptrans.domain.models import Job, SourceMeta, Timeline
from cliptrans.timeline_io import read_timeline, write_timeline

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(
        self,
        downloader: DownloaderPort,
        media_processor: MediaProcessorPort,
        transcriber: TranscriberPort,
        translator: TranslatorPort,
        job_repo: JobRepository,
        config: AppConfig,
    ) -> None:
        self._ingest = IngestService(downloader)
        self._prepare = PrepareService(media_processor)
        self._transcribe = TranscribeService(
            transcriber,
            asr_corrections=config.asr_corrections,
        )
        self._regroup = RegroupService(
            silence_threshold=config.regroup_silence_threshold,
            max_chars=config.regroup_max_chars,
        )
        self._translate = TranslateService(
            translator,
            chunk_size=config.translate_chunk_size,
            context_size=config.translate_context_size,
            default_glossary=config.glossary,
        )
        self._export = ExportService(bilingual=False)
        self._job_repo = job_repo
        self._config = config

    async def run(self, job: Job, *, local_file: Path | None = None) -> Job:
        """Execute all pipeline stages for *job*, resuming from last checkpoint.

        If *local_file* is given the INGEST stage is skipped; the file is used
        directly as the source video.
        """
        await self._ensure_data_dir(job)
        assert job.data_dir is not None
        await self._set_status(job, JobStatus.RUNNING)

        timeline = self._load_or_create_timeline(job)

        try:
            video_path: Path | None = None
            audio_path: Path | None = None

            # Stage: INGEST
            if local_file is not None:
                # Copy (or symlink) provided file into the job data dir so the
                # rest of the pipeline can find it as "video.<ext>".
                dest = job.data_dir / ("video" + local_file.suffix)
                if not dest.exists():
                    import shutil
                    shutil.copy2(local_file, dest)
                video_path = dest
                # Mark ingest as completed so --resume also skips it
                if StageKind.INGEST not in job.completed_stages:
                    job.completed_stages.append(StageKind.INGEST)
                    await self._job_repo.save(job)
            elif StageKind.INGEST not in job.completed_stages:
                await self._mark_stage(job, StageKind.INGEST)
                video_path, _ = await self._ingest.execute(job, timeline)
                await self._complete_stage(job, StageKind.INGEST)
            else:
                video_path = self._find_video(job.data_dir)

            # Stage: PREPARE
            if StageKind.PREPARE not in job.completed_stages:
                await self._mark_stage(job, StageKind.PREPARE)
                assert video_path is not None
                audio_path = await self._prepare.execute(job, timeline, video_path)
                await self._complete_stage(job, StageKind.PREPARE)
            else:
                assert job.data_dir is not None
                audio_path = job.data_dir / "audio.wav"

            # Stage: TRANSCRIBE
            if StageKind.TRANSCRIBE not in job.completed_stages:
                await self._mark_stage(job, StageKind.TRANSCRIBE)
                assert audio_path is not None
                timeline = await self._transcribe.execute(job, timeline, audio_path)
                await self._complete_stage(job, StageKind.TRANSCRIBE)

            # Stage: REGROUP
            if StageKind.REGROUP not in job.completed_stages:
                await self._mark_stage(job, StageKind.REGROUP)
                timeline = await self._regroup.execute(job, timeline)
                await self._complete_stage(job, StageKind.REGROUP)

            # Stage: TRANSLATE
            if (
                StageKind.TRANSLATE not in job.completed_stages
                and job.config.target_language != job.config.source_language
            ):
                await self._mark_stage(job, StageKind.TRANSLATE)
                timeline = await self._translate.execute(job, timeline)
                await self._complete_stage(job, StageKind.TRANSLATE)

            # Stage: EXPORT
            if StageKind.EXPORT not in job.completed_stages:
                await self._mark_stage(job, StageKind.EXPORT)
                await self._export.execute(job, timeline, video_path=video_path)
                await self._complete_stage(job, StageKind.EXPORT)

        except Exception as exc:
            logger.exception("Pipeline failed at stage %s", job.current_stage)
            job.status = JobStatus.FAILED
            job.error = str(exc)
            job.updated_at = datetime.now(UTC)
            await self._job_repo.save(job)
            raise

        job.status = JobStatus.COMPLETED
        job.current_stage = None
        job.updated_at = datetime.now(UTC)
        await self._job_repo.save(job)
        return job

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _ensure_data_dir(self, job: Job) -> None:
        if job.data_dir is None:
            job.data_dir = Path(self._config.data_dir) / "jobs" / str(job.id)
        job.data_dir.mkdir(parents=True, exist_ok=True)
        await self._job_repo.save(job)

    async def _set_status(self, job: Job, status: JobStatus) -> None:
        job.status = status
        job.updated_at = datetime.now(UTC)
        await self._job_repo.save(job)

    async def _mark_stage(self, job: Job, stage: StageKind) -> None:
        job.current_stage = stage
        job.updated_at = datetime.now(UTC)
        await self._job_repo.save(job)
        logger.info("Stage started: %s (job=%s)", stage, job.id)

    async def _complete_stage(self, job: Job, stage: StageKind) -> None:
        if stage not in job.completed_stages:
            job.completed_stages.append(stage)
        job.updated_at = datetime.now(UTC)
        await self._job_repo.save(job)
        logger.info("Stage completed: %s (job=%s)", stage, job.id)

    def _load_or_create_timeline(self, job: Job) -> Timeline:
        assert job.data_dir is not None
        timeline_path = job.data_dir / "timeline.json"
        if timeline_path.exists():
            return read_timeline(timeline_path)
        # Create a stub timeline with a placeholder source

        now = datetime.now(UTC)
        timeline = Timeline(
            job_id=job.id,
            source=SourceMeta(
                url=job.config.source_url,
                title="",
                channel="",
                duration=0,
                start_time=job.config.start_time,
                end_time=job.config.end_time,
            ),
            created_at=now,
            updated_at=now,
        )
        write_timeline(timeline, timeline_path)
        return timeline

    def _find_video(self, data_dir: Path) -> Path:
        for ext in ("mp4", "mkv", "webm"):
            candidates = list(data_dir.glob(f"video.{ext}"))
            if candidates:
                return candidates[0]
        raise FileNotFoundError(f"No video file found in {data_dir}")
