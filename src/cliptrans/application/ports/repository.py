from typing import Protocol
from uuid import UUID

from cliptrans.domain.enums import JobStatus, StageKind
from cliptrans.domain.models import Job


class JobRepository(Protocol):
    async def save(self, job: Job) -> None: ...

    async def get(self, job_id: UUID) -> Job | None: ...

    async def list_jobs(self, *, status: JobStatus | None = None) -> list[Job]: ...

    async def update_stage(
        self,
        job_id: UUID,
        stage: StageKind,
        status: JobStatus,
    ) -> None: ...

    async def delete(self, job_id: UUID) -> None: ...
