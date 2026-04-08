from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cliptrans.adapters.persistence.database import create_tables
from cliptrans.config import reset_config
from cliptrans.entrypoints.api.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "clips.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setenv("CLIPTRANS_DATABASE_URL", db_url)
    reset_config()

    import asyncio

    asyncio.run(create_tables(db_url))
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client, db_path

    reset_config()


def _insert_candidate(db_path, *, stream_id: str = "video-123") -> str:
    candidate_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clip_candidates
          (id, stream_id, start, end, title, reason, category, confidence,
           chat_intensity, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_id,
            stream_id,
            12.5,
            27.0,
            "Clip title",
            "Funny moment",
            "highlight",
            0.91,
            1.5,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return candidate_id


def _insert_selection(db_path, *, stream_id: str = "video-123", status: str = "pending") -> str:
    selection_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clip_selections
          (id, stream_id, start, end, title, notes, status,
           job_id, candidate_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            selection_id,
            stream_id,
            30.0,
            45.0,
            "Selection title",
            "Keep this one",
            status,
            None,
            None,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return selection_id


def _insert_selection_for_candidate(
    db_path, *, candidate_id: str, stream_id: str = "video-123"
) -> str:
    selection_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clip_selections
          (id, stream_id, start, end, title, notes, status,
           job_id, candidate_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            selection_id,
            stream_id,
            12.5,
            27.0,
            "Clip title",
            "",
            "pending",
            None,
            candidate_id,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return selection_id


def test_htmx_approve_accepts_form_data_and_creates_selection(client) -> None:
    test_client, db_path = client
    candidate_id = _insert_candidate(db_path)

    response = test_client.post(
        "/api/clips/approve",
        data={"candidate_id": candidate_id, "notes": ""},
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "http://testserver/stream/video-123",
        },
    )

    assert response.status_code == 200
    assert 'id="selection-count-label"' in response.text
    assert "Approved" in response.text

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT candidate_id, stream_id FROM clip_selections")
    saved_rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM clip_candidates WHERE id = ?", (candidate_id,))
    remaining_candidates = cur.fetchone()
    conn.close()

    assert saved_rows == [(candidate_id, "video-123")]
    assert remaining_candidates == (1,)


def test_htmx_create_returns_selection_card_html(client) -> None:
    test_client, _db_path = client

    response = test_client.post(
        "/api/clips/create",
        data={
            "stream_id": "video-123",
            "start": "100.0",
            "end": "125.5",
            "title": "Manual clip",
            "notes": "Created by form",
        },
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "http://testserver/stream/video-123",
        },
    )

    assert response.status_code == 200
    assert 'id="selection-count-label"' in response.text
    assert "Manual clip" in response.text
    assert '<div hx-swap-oob="beforeend:#selections-list">' in response.text
    assert 'class="clip-card"' in response.text


def test_htmx_reject_returns_updated_selection_card_html(client) -> None:
    test_client, db_path = client
    selection_id = _insert_selection(db_path)

    response = test_client.post(
        f"/api/clips/selections/{selection_id}/reject",
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "http://testserver/selections",
        },
    )

    assert response.status_code == 200
    assert "badge-status-rejected" in response.text
    assert "Delete" in response.text
    assert "btn-reject" not in response.text


def test_htmx_delete_returns_selection_count_update_for_stream_page(client) -> None:
    test_client, db_path = client
    selection_id = _insert_selection(db_path)

    response = test_client.delete(
        f"/api/clips/selections/{selection_id}",
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "http://testserver/stream/video-123",
        },
    )

    assert response.status_code == 200
    assert 'id="selection-count-label"' in response.text
    assert "Removed selection." in response.text

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clip_selections WHERE id = ?", (selection_id,))
    remaining = cur.fetchone()
    conn.close()

    assert remaining == (0,)


def test_htmx_delete_returns_candidate_to_stream_page(client) -> None:
    test_client, db_path = client
    candidate_id = _insert_candidate(db_path)
    selection_id = _insert_selection_for_candidate(db_path, candidate_id=candidate_id)

    response = test_client.delete(
        f"/api/clips/selections/{selection_id}",
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "http://testserver/stream/video-123",
        },
    )

    assert response.status_code == 200
    assert 'id="candidate-count-label"' in response.text
    assert "Returned" in response.text
    assert 'hx-swap-oob="beforeend:#candidates-list"' in response.text
    assert "Clip title" in response.text
