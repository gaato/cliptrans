"""Clip candidates and selections API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cliptrans.domain.models import ClipCandidate, ClipSelection
from cliptrans.entrypoints.api.deps import ClipFinder, ClipManager, ClipRepo

router = APIRouter()


class ApproveRequest(BaseModel):
    candidate_id: UUID
    notes: str = ""


class CreateSelectionRequest(BaseModel):
    stream_id: str
    start: float
    end: float
    title: str
    notes: str = ""


class FindRequest(BaseModel):
    video_id: str


@router.post("/find", response_model=list[ClipCandidate])
async def find_candidates(body: FindRequest, finder: ClipFinder, repo: ClipRepo):
    candidates = await finder.find_candidates(body.video_id)
    await repo.save_candidates(candidates)
    return candidates


@router.get("/candidates/{stream_id}", response_model=list[ClipCandidate])
async def get_candidates(stream_id: str, repo: ClipRepo):
    return await repo.get_candidates(stream_id)


@router.get("/selections", response_model=list[ClipSelection])
async def list_selections(
    repo: ClipRepo,
    stream_id: str | None = Query(None),
    status: str | None = Query(None),
):
    return await repo.get_selections(stream_id=stream_id, status=status)


@router.post("/approve", response_model=ClipSelection)
async def approve_candidate(body: ApproveRequest, repo: ClipRepo, manager: ClipManager):
    candidate = await repo.get_candidate(body.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return await manager.approve_candidate(candidate, notes=body.notes)


@router.post("/create", response_model=ClipSelection)
async def create_selection(body: CreateSelectionRequest, manager: ClipManager):
    return await manager.create_selection(
        stream_id=body.stream_id,
        start=body.start,
        end=body.end,
        title=body.title,
        notes=body.notes,
    )


@router.delete("/selections/{selection_id}", status_code=204)
async def delete_selection(selection_id: UUID, manager: ClipManager):
    await manager.delete_selection(selection_id)


@router.post("/selections/{selection_id}/reject", response_model=ClipSelection)
async def reject_selection(selection_id: UUID, manager: ClipManager):
    sel = await manager.reject_selection(selection_id)
    if sel is None:
        raise HTTPException(status_code=404, detail="Selection not found")
    return sel
