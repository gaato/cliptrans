"""Read and write timeline.json — the canonical source of truth for a job."""

from __future__ import annotations

import json
from pathlib import Path

from cliptrans.domain.errors import TimelineError
from cliptrans.domain.models import Timeline

SUPPORTED_VERSIONS = {"1.0"}


def read_timeline(path: Path) -> Timeline:
    """Load a timeline.json from *path* and validate it."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TimelineError(f"Cannot read timeline from {path}: {exc}") from exc

    version = raw.get("version", "unknown")
    if version not in SUPPORTED_VERSIONS:
        raise TimelineError(
            f"Unsupported timeline version {version!r}. Supported: {sorted(SUPPORTED_VERSIONS)}"
        )

    try:
        return Timeline.model_validate(raw)
    except Exception as exc:
        raise TimelineError(f"Invalid timeline schema in {path}: {exc}") from exc


def write_timeline(timeline: Timeline, path: Path) -> None:
    """Serialise *timeline* to *path* as JSON (UTF-8, pretty-printed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            timeline.model_dump_json(indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise TimelineError(f"Cannot write timeline to {path}: {exc}") from exc
