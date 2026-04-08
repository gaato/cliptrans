"""SQLAlchemy implementation of ClipRepository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from cliptrans.adapters.persistence.database import session_scope
from cliptrans.adapters.persistence.tables import ClipCandidateRow, ClipSelectionRow
from cliptrans.domain.enums import ClipStatus
from cliptrans.domain.models import ClipCandidate, ClipSelection


def _row_to_candidate(row: ClipCandidateRow) -> ClipCandidate:
    return ClipCandidate(
        id=UUID(row.id),
        stream_id=row.stream_id,
        start=row.start,
        end=row.end,
        title=row.title,
        reason=row.reason,
        category=row.category,
        confidence=row.confidence,
        chat_intensity=row.chat_intensity,
        created_at=row.created_at,
    )


def _candidate_to_row(c: ClipCandidate) -> ClipCandidateRow:
    return ClipCandidateRow(
        id=str(c.id),
        stream_id=c.stream_id,
        start=c.start,
        end=c.end,
        title=c.title,
        reason=c.reason,
        category=c.category,
        confidence=c.confidence,
        chat_intensity=c.chat_intensity,
        created_at=c.created_at,
    )


def _row_to_selection(row: ClipSelectionRow) -> ClipSelection:
    return ClipSelection(
        id=UUID(row.id),
        stream_id=row.stream_id,
        start=row.start,
        end=row.end,
        title=row.title,
        notes=row.notes,
        status=ClipStatus(row.status),
        job_id=UUID(row.job_id) if row.job_id else None,
        candidate_id=UUID(row.candidate_id) if row.candidate_id else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _selection_to_row(s: ClipSelection) -> ClipSelectionRow:
    return ClipSelectionRow(
        id=str(s.id),
        stream_id=s.stream_id,
        start=s.start,
        end=s.end,
        title=s.title,
        notes=s.notes,
        status=str(s.status),
        job_id=str(s.job_id) if s.job_id else None,
        candidate_id=str(s.candidate_id) if s.candidate_id else None,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


class SQLAlchemyClipRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    # Candidates

    async def save_candidate(self, candidate: ClipCandidate) -> None:
        async with session_scope(self._database_url) as session:
            existing = await session.get(ClipCandidateRow, str(candidate.id))
            row = _candidate_to_row(candidate)
            if existing is None:
                session.add(row)
            else:
                for col in row.__table__.columns:
                    setattr(existing, col.name, getattr(row, col.name))

    async def save_candidates(self, candidates: list[ClipCandidate]) -> None:
        for c in candidates:
            await self.save_candidate(c)

    async def get_candidates(self, stream_id: str) -> list[ClipCandidate]:
        async with session_scope(self._database_url) as session:
            stmt = select(ClipCandidateRow).where(ClipCandidateRow.stream_id == stream_id)
            result = await session.execute(stmt)
            return [_row_to_candidate(r) for r in result.scalars()]

    async def get_candidate(self, candidate_id: UUID) -> ClipCandidate | None:
        async with session_scope(self._database_url) as session:
            row = await session.get(ClipCandidateRow, str(candidate_id))
            return _row_to_candidate(row) if row else None

    async def delete_candidate(self, candidate_id: UUID) -> None:
        async with session_scope(self._database_url) as session:
            row = await session.get(ClipCandidateRow, str(candidate_id))
            if row:
                await session.delete(row)

    async def delete_candidates(self, stream_id: str) -> None:
        async with session_scope(self._database_url) as session:
            result = await session.execute(
                select(ClipCandidateRow).where(ClipCandidateRow.stream_id == stream_id)
            )
            for row in result.scalars():
                await session.delete(row)

    # Selections

    async def save_selection(self, selection: ClipSelection) -> None:
        async with session_scope(self._database_url) as session:
            existing = await session.get(ClipSelectionRow, str(selection.id))
            row = _selection_to_row(selection)
            if existing is None:
                session.add(row)
            else:
                for col in row.__table__.columns:
                    setattr(existing, col.name, getattr(row, col.name))

    async def get_selections(
        self, *, stream_id: str | None = None, status: str | None = None
    ) -> list[ClipSelection]:
        async with session_scope(self._database_url) as session:
            stmt = select(ClipSelectionRow)
            if stream_id:
                stmt = stmt.where(ClipSelectionRow.stream_id == stream_id)
            if status:
                stmt = stmt.where(ClipSelectionRow.status == status)
            result = await session.execute(stmt)
            return [_row_to_selection(r) for r in result.scalars()]

    async def get_selection(self, selection_id: UUID) -> ClipSelection | None:
        async with session_scope(self._database_url) as session:
            row = await session.get(ClipSelectionRow, str(selection_id))
            return _row_to_selection(row) if row else None

    async def update_selection(self, selection: ClipSelection) -> None:
        async with session_scope(self._database_url) as session:
            existing = await session.get(ClipSelectionRow, str(selection.id))
            if existing is None:
                return
            row = _selection_to_row(selection)
            for col in row.__table__.columns:
                setattr(existing, col.name, getattr(row, col.name))

    async def delete_selection(self, selection_id: UUID) -> None:
        async with session_scope(self._database_url) as session:
            row = await session.get(ClipSelectionRow, str(selection_id))
            if row:
                await session.delete(row)
