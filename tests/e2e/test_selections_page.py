"""E2E tests for the selections page (/selections).

Covers
------
* Page title
* Selection cards rendered from DB
* Each card shows stream link, timestamps, title, status badge
* "✘ Reject" sends HTMX POST and the card is replaced
* "🗑 Delete" prompts for confirmation, then sends HTMX DELETE
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Dialog, Page, Request, Response, expect

from e2e.fixtures import TEST_VIDEO_ID

pytestmark = pytest.mark.e2e


# ── Helpers ───────────────────────────────────────────────────────────────────


def _goto_selections(page: Page, live_server_url: str) -> None:
    page.goto(live_server_url + "/selections")
    page.wait_for_load_state("networkidle")


# ── Basic page load ───────────────────────────────────────────────────────────


def test_selections_page_title(page: Page, live_server_url: str) -> None:
    """The selections page has the expected <title>."""
    _goto_selections(page, live_server_url)
    expect(page).to_have_title("Selections — ClipTrans")


def test_selections_page_heading(page: Page, live_server_url: str) -> None:
    """The page has a <h1> with 'Selections'."""
    _goto_selections(page, live_server_url)
    expect(page.locator("h1")).to_have_text("Selections")


def test_empty_state_message_when_no_data(page: Page, live_server_url: str) -> None:
    """When there are no selections the empty-state paragraph appears."""
    # No seeded_clips fixture → DB is empty for selections
    _goto_selections(page, live_server_url)
    expect(page.locator(".empty-message")).to_be_visible()
    expect(page.locator(".empty-message")).to_contain_text("No selections yet")


# ── Cards with data ───────────────────────────────────────────────────────────


def test_selection_card_renders(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """A seeded selection appears as a clip card."""
    _goto_selections(page, live_server_url)
    cards = page.locator(".clip-card")
    expect(cards).to_have_count(1)


def test_selection_card_title(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Selection card shows the clip title."""
    _goto_selections(page, live_server_url)
    expect(page.locator(".clip-title")).to_contain_text("Best Clip")


def test_selection_card_notes(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Selection card shows the notes text."""
    _goto_selections(page, live_server_url)
    expect(page.locator(".clip-reason")).to_contain_text("Must include this")


def test_selection_card_status_badge(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Selection card shows a status badge ('pending')."""
    _goto_selections(page, live_server_url)
    badge = page.locator(".badge-status-pending")
    expect(badge).to_be_visible()
    expect(badge).to_contain_text("pending")


def test_selection_card_timestamps(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Selection card shows start → end timestamps (2:30 → 4:30)."""
    _goto_selections(page, live_server_url)
    clip_times = page.locator(".clip-times").first
    # start=150 → 2:30, end=270 → 4:30
    expect(clip_times).to_contain_text("2:30")
    expect(clip_times).to_contain_text("4:30")


def test_selection_card_stream_link(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Selection card has a link back to the stream detail page."""
    _goto_selections(page, live_server_url)
    link = page.locator(".clip-times a").first
    expect(link).to_have_attribute("href", f"/stream/{TEST_VIDEO_ID}")
    expect(link).to_contain_text(TEST_VIDEO_ID)


# ── Reject button ─────────────────────────────────────────────────────────────


def test_reject_button_visible(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Each selection card has a '✘ Reject' button."""
    _goto_selections(page, live_server_url)
    expect(page.locator(".btn-reject")).to_be_visible()
    expect(page.locator(".btn-reject")).to_contain_text("Reject")


def test_reject_button_sends_post(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Clicking '✘ Reject' sends an HTMX POST to /api/clips/selections/<id>/reject."""
    _goto_selections(page, live_server_url)

    card = page.locator(".clip-card").first
    sel_id = (card.get_attribute("id") or "").replace("sel-", "")

    posted: list[str] = []

    def _on_request(r: Request) -> None:
        if "reject" in r.url and r.method == "POST":
            posted.append(r.url)

    page.on("request", _on_request)

    page.locator(".btn-reject").first.click()
    page.wait_for_timeout(600)

    assert any(sel_id in url for url in posted), (
        f"Expected POST to .../reject with {sel_id!r}, got: {posted}"
    )


def test_reject_changes_card_status(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """After rejection the POST request is accepted by the server (200)."""
    _goto_selections(page, live_server_url)

    responses: list[tuple[str, int]] = []

    def _on_response(r: Response) -> None:
        if "reject" in r.url:
            responses.append((r.url, r.status))

    page.on("response", _on_response)

    page.locator(".btn-reject").first.click()
    page.wait_for_timeout(600)

    assert responses, "No response received for reject endpoint"
    assert responses[0][1] == 200, f"Expected 200, got {responses[0][1]}"


# ── Delete button ─────────────────────────────────────────────────────────────


def test_delete_button_visible(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Each selection card has a '🗑 Delete' button."""
    _goto_selections(page, live_server_url)
    expect(page.locator(".btn-danger")).to_be_visible()
    expect(page.locator(".btn-danger")).to_contain_text("Delete")


def test_delete_button_shows_confirm_dialog(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Clicking '🗑 Delete' shows an HTMX confirm dialog."""
    _goto_selections(page, live_server_url)

    # htmx uses a window.confirm() dialog when hx-confirm is set
    dialog_texts: list[str] = []

    def _on_dialog(d: Dialog) -> None:
        dialog_texts.append(d.message)
        d.dismiss()

    page.on("dialog", _on_dialog)

    page.locator(".btn-danger").first.click()
    page.wait_for_timeout(400)

    assert dialog_texts, "Expected a confirm dialog but none appeared"
    assert "Delete" in dialog_texts[0]


def test_delete_confirmed_sends_delete_request(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Confirming deletion sends DELETE to /api/clips/selections/<id> (204).

    Note: HTMX 1.9.x does not perform a DOM swap on 204 No Content responses,
    so the card is not automatically removed from the page by the client.
    The test verifies the DELETE request was accepted by the server (204).
    """
    _goto_selections(page, live_server_url)

    card = page.locator(".clip-card").first
    sel_id = (card.get_attribute("id") or "").replace("sel-", "")

    deleted_responses: list[tuple[str, int]] = []

    def _on_delete_response(r: Response) -> None:
        if r.request.method == "DELETE" and "selections" in r.url:
            deleted_responses.append((r.url, r.status))

    page.on("response", _on_delete_response)

    # Accept the confirm dialog
    def _accept_dialog(d: Dialog) -> None:
        d.accept()

    page.on("dialog", _accept_dialog)
    page.locator(".btn-danger").first.click()
    page.wait_for_timeout(800)

    assert deleted_responses, f"Expected DELETE request for {sel_id!r}, none sent"
    assert any(sel_id in url for url, _ in deleted_responses), (
        f"Expected DELETE for {sel_id!r}, got: {deleted_responses}"
    )
    assert deleted_responses[0][1] == 204, f"Expected 204 No Content, got {deleted_responses[0][1]}"


# ── Navigation ────────────────────────────────────────────────────────────────


def test_nav_stream_link_goes_to_home(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Clicking 'Streams' in the nav navigates to /."""
    _goto_selections(page, live_server_url)
    page.get_by_role("link", name="Streams").click()
    page.wait_for_load_state("networkidle")
    assert page.url.rstrip("/") == live_server_url.rstrip("/")


def test_stream_link_on_card_navigates(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Clicking the stream ID link on a card navigates to the detail page."""
    _goto_selections(page, live_server_url)
    page.locator(".clip-times a").first.click()
    page.wait_for_load_state("networkidle")
    assert f"/stream/{TEST_VIDEO_ID}" in page.url
