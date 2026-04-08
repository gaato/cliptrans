"""Shared fixtures for E2E browser tests.

Architecture
------------
* ``live_server_url`` — Session-scoped fixture that starts a real uvicorn server
  with two dependency overrides injected:

    1. ``MockHolodex`` — replaces the Holodex API adapter so the tests never
       hit the real Holodex service.  It returns a fixed Takanashi Kiara channel
       and a single Kiara stream.

    2. ``SQLAlchemyClipRepository`` pointed at a temp file-backed SQLite DB so
       that clip candidates / selections can be read and written normally.

* ``seeded_clips`` — Function-scoped fixture that inserts test clip candidates
  and one selection into the DB before each test and removes them afterwards.

Channel autocomplete and the ``suggest`` API
--------------------------------------------
The channel-search autocomplete (Alpine.js + ``fetch()``) calls
``GET /api/streams/channels/suggest?q=<query>``.  Since that endpoint goes
through ``MockHolodex.search_channels()``, tests work without network access
and without a real Holodex API key.  The mock returns Takanashi Kiara for any
query that contains "kiara" or "takanashi".

For tests that want to override even the server mock (e.g. simulating an error
response or a completely different result set), ``page.route()`` intercepts the
request at the browser level and short-circuits it before it reaches the
server — the ``test_channel_autocomplete_api_error`` test demonstrates this.
"""

from __future__ import annotations

import socket
import sqlite3
import threading
import time
import urllib.request
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn

from cliptrans.adapters.persistence.clip_repository import SQLAlchemyClipRepository
from cliptrans.adapters.persistence.database import create_tables
from cliptrans.application.services.stream_browser import StreamBrowserService
from cliptrans.domain.models import ChannelInfo, StreamInfo
from cliptrans.entrypoints.api.app import create_app
from cliptrans.entrypoints.api.deps import _clip_repo, _stream_browser
from e2e.fixtures import KIARA_CHANNEL, KIARA_CHANNEL_ID, KIARA_STREAM, TEST_VIDEO_ID

__all__ = ["KIARA_CHANNEL_ID", "KIARA_STREAM", "TEST_VIDEO_ID"]


class MockHolodex:
    """Holodex adapter stub that returns Takanashi Kiara fixture data."""

    async def search_channels(self, query: str, *, limit: int = 10) -> list[ChannelInfo]:
        q = query.lower()
        if any(kw in q for kw in ("kiara", "takanashi", "kiar", "taka")):
            return [KIARA_CHANNEL]
        return []

    async def list_live_streams(self, *, org=None, limit=50) -> list[StreamInfo]:
        return []

    async def list_past_streams(self, *, channel_id=None, org=None, limit=50) -> list[StreamInfo]:
        streams = [KIARA_STREAM]
        if channel_id and channel_id != KIARA_CHANNEL_ID:
            return []
        if org and org.lower() not in (KIARA_STREAM.org or "").lower():
            return []
        return streams[:limit]

    async def get_stream(self, video_id: str) -> StreamInfo:
        if video_id == TEST_VIDEO_ID:
            return KIARA_STREAM
        from cliptrans.domain.errors import HolodexError

        raise HolodexError(f"Stream {video_id!r} not found in mock")


# Live server


def _get_free_port() -> int:
    """Return an ephemeral port that is free on 127.0.0.1 at the time of calling."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Live server at {url} did not start within {timeout}s")


@pytest.fixture(scope="session")
def e2e_db_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return the path to the session-scoped SQLite DB file."""
    return tmp_path_factory.mktemp("e2e") / "test.db"


@pytest.fixture(scope="session")
def e2e_db_url(e2e_db_file: Path) -> str:
    return f"sqlite+aiosqlite:///{e2e_db_file.resolve()}"


@pytest.fixture(scope="session")
def live_server_url(e2e_db_file: Path, e2e_db_url: str) -> Generator[str]:
    """Start uvicorn in a background daemon thread.  Returns the base URL.

    The server uses:
    * ``MockHolodex`` — no real Holodex calls
    * A file-backed SQLite DB shared across the session
    """
    import asyncio

    # Initialise tables (sync wrapper around the async helper)
    asyncio.run(create_tables(e2e_db_url))

    app = create_app()
    mock_browser = StreamBrowserService(MockHolodex())
    mock_repo = SQLAlchemyClipRepository(e2e_db_url)

    app.dependency_overrides[_stream_browser] = lambda: mock_browser
    app.dependency_overrides[_clip_repo] = lambda: mock_repo

    port = _get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server(base_url + "/")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


# DB seeding


@pytest.fixture()
def seeded_clips(e2e_db_file: Path) -> Generator[dict]:  # type: ignore[type-arg]
    """Insert clip candidates and one selection; clean up after the test.

    Uses raw ``sqlite3`` to avoid async/event-loop conflicts with pytest-asyncio.

    Returns a dict with keys ``candidates`` (list of dicts) and ``selection``
    (dict) so tests can refer to their IDs.
    """
    conn = sqlite3.connect(e2e_db_file)
    cur = conn.cursor()
    now = datetime.now(UTC).isoformat()

    candidate_rows = []
    for i in range(3):
        cid = str(uuid4())
        cur.execute(
            """
            INSERT INTO clip_candidates
              (id, stream_id, start, end, title, reason, category, confidence,
               chat_intensity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                TEST_VIDEO_ID,
                i * 300.0,
                i * 300.0 + 120.0,
                f"Funny Moment {i + 1}",
                f"Kiara laughed hard #{i + 1}",
                "highlight",
                0.9 - i * 0.05,
                float(i + 1) * 2.0,
                now,
            ),
        )
        candidate_rows.append({"id": cid, "title": f"Funny Moment {i + 1}"})

    sel_id = str(uuid4())
    cur.execute(
        """
        INSERT INTO clip_selections
          (id, stream_id, start, end, title, notes, status,
           job_id, candidate_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sel_id,
            TEST_VIDEO_ID,
            150.0,
            270.0,
            "Best Clip",
            "Must include this",
            "pending",
            None,
            candidate_rows[0]["id"],
            now,
            now,
        ),
    )

    conn.commit()
    conn.close()

    yield {"candidates": candidate_rows, "selection": {"id": sel_id}}

    # Cleanup — remove only the rows this fixture inserted
    conn = sqlite3.connect(e2e_db_file)
    cur = conn.cursor()
    cur.execute("DELETE FROM clip_candidates WHERE stream_id = ?", (TEST_VIDEO_ID,))
    cur.execute("DELETE FROM clip_selections WHERE stream_id = ?", (TEST_VIDEO_ID,))
    conn.commit()
    conn.close()
