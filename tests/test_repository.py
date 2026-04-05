"""Integration tests for SQLAlchemy SQLite repository (in-memory)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cliptrans.adapters.persistence.database import create_tables
from cliptrans.adapters.persistence.repository import SQLAlchemyJobRepository
from cliptrans.domain.enums import JobStatus, StageKind
from cliptrans.domain.errors import JobNotFoundError
from cliptrans.domain.models import Job, JobConfig

DB_URL = "sqlite+aiosqlite://"  # in-memory


@pytest.fixture()
async def repo() -> SQLAlchemyJobRepository:
    await create_tables(DB_URL)
    return SQLAlchemyJobRepository(database_url=DB_URL)


@pytest.fixture()
def sample_job() -> Job:
    now = datetime.now(UTC)
    return Job(
        config=JobConfig(source_url="https://example.com/v?id=test"),
        created_at=now,
        updated_at=now,
    )


class TestJobRepository:
    async def test_save_and_get(self, repo, sample_job):
        await repo.save(sample_job)
        fetched = await repo.get(sample_job.id)
        assert fetched is not None
        assert fetched.id == sample_job.id
        assert fetched.status == JobStatus.PENDING

    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get(uuid4())
        assert result is None

    async def test_save_updates_existing(self, repo, sample_job):
        await repo.save(sample_job)
        sample_job.status = JobStatus.RUNNING
        await repo.save(sample_job)
        fetched = await repo.get(sample_job.id)
        assert fetched is not None
        assert fetched.status == JobStatus.RUNNING

    async def test_list_jobs_all(self, repo, sample_job):
        await repo.save(sample_job)
        jobs = await repo.list_jobs()
        assert any(j.id == sample_job.id for j in jobs)

    async def test_list_jobs_by_status(self, repo, sample_job):
        await repo.save(sample_job)
        pending = await repo.list_jobs(status=JobStatus.PENDING)
        running = await repo.list_jobs(status=JobStatus.RUNNING)
        assert any(j.id == sample_job.id for j in pending)
        assert not any(j.id == sample_job.id for j in running)

    async def test_update_stage(self, repo, sample_job):
        await repo.save(sample_job)
        await repo.update_stage(sample_job.id, StageKind.INGEST, JobStatus.RUNNING)
        fetched = await repo.get(sample_job.id)
        assert fetched is not None
        assert fetched.current_stage == StageKind.INGEST

    async def test_update_stage_completed_adds_to_list(self, repo, sample_job):
        await repo.save(sample_job)
        await repo.update_stage(sample_job.id, StageKind.INGEST, JobStatus.COMPLETED)
        fetched = await repo.get(sample_job.id)
        assert fetched is not None
        assert StageKind.INGEST in fetched.completed_stages

    async def test_update_stage_not_found_raises(self, repo):
        with pytest.raises(JobNotFoundError):
            await repo.update_stage(uuid4(), StageKind.INGEST, JobStatus.RUNNING)

    async def test_delete(self, repo, sample_job):
        await repo.save(sample_job)
        await repo.delete(sample_job.id)
        assert await repo.get(sample_job.id) is None

    async def test_config_roundtrip(self, repo, sample_job):
        await repo.save(sample_job)
        fetched = await repo.get(sample_job.id)
        assert fetched is not None
        assert fetched.config.source_url == sample_job.config.source_url
