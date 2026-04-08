"""Clip candidates and selections API endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError

from cliptrans.domain.models import ClipCandidate, ClipSelection
from cliptrans.entrypoints.api.deps import ClipFinder, ClipManager, ClipRepo
from cliptrans.entrypoints.api.i18n import preferred_language

router = APIRouter()
_templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


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


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _current_page_kind(request: Request) -> str:
    current_url = request.headers.get("HX-Current-URL", "")
    current_path = urlparse(current_url).path
    if current_path.startswith("/stream/"):
        return "stream"
    return "selections"


async def _parse_request_model[RequestModelT: BaseModel](
    request: Request, model_cls: type[RequestModelT]
) -> RequestModelT:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    else:
        payload = dict(await request.form())

    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


def _selection_response(request: Request, selection: ClipSelection):
    if not _is_htmx(request):
        return selection
    return _templates.TemplateResponse(
        request=request,
        name="_selection_card.html",
        context={"s": selection, "page_kind": _current_page_kind(request)},
    )


async def _stream_counts(repo: ClipRepo, stream_id: str) -> tuple[int, int]:
    candidates = await repo.get_candidates(stream_id)
    selections = await repo.get_selections(stream_id=stream_id, status="pending")
    return len(candidates), len(selections)


def _template_response(
    request: Request,
    name: str,
    context: Mapping[str, object],
):
    return _templates.TemplateResponse(request=request, name=name, context=dict(context))


@router.post("/find", response_model=list[ClipCandidate])
async def find_candidates(
    request: Request, body: FindRequest, finder: ClipFinder, repo: ClipRepo
):
    candidates = await finder.find_candidates(
        body.video_id, output_language=preferred_language(request)
    )
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
async def approve_candidate(request: Request, repo: ClipRepo, manager: ClipManager):
    body = await _parse_request_model(request, ApproveRequest)
    candidate = await repo.get_candidate(body.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    selection = await manager.approve_candidate(candidate, notes=body.notes)
    await repo.delete_candidate(candidate.id)
    if _is_htmx(request):
        candidate_count, selection_count = await _stream_counts(repo, candidate.stream_id)
        return _template_response(
            request=request,
            name="_approve_candidate_result.html",
            context={
                "selection": selection,
                "candidate_count": candidate_count,
                "selection_count": selection_count,
            },
        )
    return selection


@router.post("/create", response_model=ClipSelection)
async def create_selection(request: Request, manager: ClipManager):
    body = await _parse_request_model(request, CreateSelectionRequest)
    selection = await manager.create_selection(
        stream_id=body.stream_id,
        start=body.start,
        end=body.end,
        title=body.title,
        notes=body.notes,
    )
    if _is_htmx(request):
        selection_count = len(
            await manager.list_selections(stream_id=body.stream_id, status="pending")
        )
        return _template_response(
            request=request,
            name="_create_selection_result.html",
            context={"selection": selection, "selection_count": selection_count},
        )
    return _selection_response(request, selection)


@router.delete("/selections/{selection_id}")
async def delete_selection(
    request: Request, selection_id: UUID, repo: ClipRepo, manager: ClipManager
):
    selection = await repo.get_selection(selection_id)
    if selection is None:
        raise HTTPException(status_code=404, detail="Selection not found")
    await manager.delete_selection(selection_id)
    if not _is_htmx(request):
        return Response(status_code=204)
    selection_count = len(
        await manager.list_selections(stream_id=selection.stream_id, status="pending")
    )
    return _template_response(
        request=request,
        name="_delete_selection_result.html",
        context={"selection_count": selection_count, "page_kind": _current_page_kind(request)},
    )


@router.post("/selections/{selection_id}/reject", response_model=ClipSelection)
async def reject_selection(request: Request, selection_id: UUID, manager: ClipManager):
    sel = await manager.reject_selection(selection_id)
    if sel is None:
        raise HTTPException(status_code=404, detail="Selection not found")
    return _selection_response(request, sel)
