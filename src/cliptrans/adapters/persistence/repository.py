"""SQLAlchemy implementation of JobRepository."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from cliptrans.adapters.persistence.database import session_scope
from cliptrans.adapters.persistence.tables import JobRow
from cliptrans.domain.enums import JobStatus, StageKind
from cliptrans.domain.errors import JobNotFoundError
from cliptrans.domain.models import Job, JobConfig


def _row_to_job(row: JobRow) -> Job:
    return Job(
        id=UUID(row.id),
        config=JobConfig.model_validate_json(row.config_json),
        status=JobStatus(row.status),
        current_stage=StageKind(row.current_stage) if row.current_stage else None,
        completed_stages=[StageKind(s) for s in json.loads(row.completed_stages)],
        error=row.error,
        data_dir=Path(row.data_dir) if row.data_dir else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _job_to_row(job: Job) -> JobRow:
    return JobRow(
        id=str(job.id),
        status=job.status,
        current_stage=job.current_stage,
        completed_stages=json.dumps([str(s) for s in job.completed_stages]),
        config_json=job.config.model_dump_json(),
        error=job.error,
        data_dir=str(job.data_dir) if job.data_dir else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


class SQLAlchemyJobRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def save(self, job: Job) -> None:
        async with session_scope(self._database_url) as session:
            existing = await session.get(JobRow, str(job.id))
            row = _job_to_row(job)
            if existing is None:
                session.add(row)
            else:
                for col in row.__table__.columns:
                    setattr(existing, col.name, getattr(row, col.name))

    async def get(self, job_id: UUID) -> Job | None:
        async with session_scope(self._database_url) as session:
            row = await session.get(JobRow, str(job_id))
            return _row_to_job(row) if row else None

    async def list_jobs(self, *, status: JobStatus | None = None) -> list[Job]:
        async with session_scope(self._database_url) as session:
            stmt = select(JobRow)
            if status is not None:
                stmt = stmt.where(JobRow.status == str(status))
            result = await session.execute(stmt)
            return [_row_to_job(r) for r in result.scalars()]

    async def update_stage(
        self,
        job_id: UUID,
        stage: StageKind,
        status: JobStatus,
    ) -> None:
        async with session_scope(self._database_url) as session:
            row = await session.get(JobRow, str(job_id))
            if row is None:
                raise JobNotFoundError(job_id)
            row.current_stage = str(stage)
            row.status = str(status)
            stages = json.loads(row.completed_stages)
            if status == JobStatus.COMPLETED and str(stage) not in stages:
                stages.append(str(stage))
            row.completed_stages = json.dumps(stages)
            row.updated_at = datetime.now(UTC)

    async def delete(self, job_id: UUID) -> None:
        async with session_scope(self._database_url) as session:
            row = await session.get(JobRow, str(job_id))
            if row is not None:
                await session.delete(row)
