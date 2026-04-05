"""Clip manager service — approve/reject candidates and track selections."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from cliptrans.application.ports.clip_repository import ClipRepositoryPort
from cliptrans.domain.enums import ClipStatus
from cliptrans.domain.models import ClipCandidate, ClipSelection


class ClipManagerService:
    def __init__(self, clip_repo: ClipRepositoryPort) -> None:
        self._repo = clip_repo

    async def approve_candidate(
        self, candidate: ClipCandidate, notes: str = ""
    ) -> ClipSelection:
        now = datetime.now(UTC)
        selection = ClipSelection(
            stream_id=candidate.stream_id,
            start=candidate.start,
            end=candidate.end,
            title=candidate.title,
            notes=notes,
            status=ClipStatus.PENDING,
            candidate_id=candidate.id,
            created_at=now,
            updated_at=now,
        )
        await self._repo.save_selection(selection)
        return selection

    async def create_selection(
        self,
        stream_id: str,
        start: float,
        end: float,
        title: str,
        notes: str = "",
    ) -> ClipSelection:
        now = datetime.now(UTC)
        selection = ClipSelection(
            stream_id=stream_id,
            start=start,
            end=end,
            title=title,
            notes=notes,
            status=ClipStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        await self._repo.save_selection(selection)
        return selection

    async def reject_selection(self, selection_id: UUID) -> ClipSelection | None:
        sel = await self._repo.get_selection(selection_id)
        if sel is None:
            return None
        sel = sel.model_copy(
            update={"status": ClipStatus.REJECTED, "updated_at": datetime.now(UTC)}
        )
        await self._repo.update_selection(sel)
        return sel

    async def list_selections(
        self, *, stream_id: str | None = None, status: str | None = None
    ) -> list[ClipSelection]:
        return await self._repo.get_selections(stream_id=stream_id, status=status)

    async def delete_selection(self, selection_id: UUID) -> None:
        await self._repo.delete_selection(selection_id)
