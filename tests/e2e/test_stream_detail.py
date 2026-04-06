"""E2E tests for the stream detail page (/stream/<video_id>).

Covers
------
* Page header (title, channel, duration)
* Default tab is 候補 (Candidates)
* Candidate cards show time buttons, title, reason, category badge, conf badge
* Tab switching to 確定 (Selections) and 文字起こし (Transcript)
* Transcript tab fires an HTMX GET request to /htmx/transcript/<video_id>
* 「🤖 AI でクリップ候補を探す」 button visible and enabled
* 「✔ 採用」 (Approve) HTMX POST is sent with the correct candidate_id
* 「✘ 却下」 (Reject) button is visible in the selections tab
* Manual clip form (``<details>``) opens and has the expected fields
* Time buttons (seekTo) carry correct timestamps
"""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import Page, Request, expect

from e2e.fixtures import TEST_VIDEO_ID

pytestmark = pytest.mark.e2e

_DETAIL_PATH = f"/stream/{TEST_VIDEO_ID}"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _open_detail(page: Page, live_server_url: str) -> None:
    page.goto(live_server_url + _DETAIL_PATH)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)  # allow Alpine.js to initialise


# ── Page header ───────────────────────────────────────────────────────────────


def test_detail_page_title(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """Title tag contains the stream title."""
    _open_detail(page, live_server_url)
    expect(page).to_have_title(re.compile("Kiara"))


def test_detail_stream_heading(page: Page, live_server_url: str, seeded_clips: dict) -> None:
    """The <h1> shows the stream title."""
    _open_detail(page, live_server_url)
    expect(page.locator("h1")).to_contain_text("Kiara")


def test_detail_meta_shows_channel_and_org(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The subtitle line includes channel name, org, and duration."""
    _open_detail(page, live_server_url)
    meta = page.locator(".stream-meta")
    expect(meta).to_contain_text("Takanashi Kiara")
    expect(meta).to_contain_text("Hololive")
    expect(meta).to_contain_text("2h")


def test_detail_yt_player_area_exists(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The YouTube player wrapper element is present in the DOM."""
    _open_detail(page, live_server_url)
    expect(page.locator("#yt-player-wrapper")).to_be_attached()


def test_detail_seek_input_and_button(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The seek controls (number input and ▶ Seek button) are visible."""
    _open_detail(page, live_server_url)
    expect(page.locator("#seek-input")).to_be_visible()
    expect(page.get_by_role("button", name="▶ Seek")).to_be_visible()


# ── Candidate tab (default) ───────────────────────────────────────────────────


def test_candidates_tab_is_active_by_default(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The 候補 tab button has the 'active' class on first load."""
    _open_detail(page, live_server_url)
    candidates_tab = page.locator(".tab-bar button").nth(0)
    assert "active" in (candidates_tab.get_attribute("class") or "")


def test_candidate_cards_visible(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """All three seeded clip candidates appear as cards."""
    _open_detail(page, live_server_url)
    cards = page.locator("#candidates-list .clip-card")
    expect(cards).to_have_count(3)


def test_candidate_card_shows_title(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Each candidate card shows its title text."""
    _open_detail(page, live_server_url)
    first_card = page.locator("#candidates-list .clip-card").first
    expect(first_card.locator(".clip-title")).to_contain_text("Funny Moment")


def test_candidate_card_shows_time_buttons(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Candidate cards display start and end time buttons (m:ss format)."""
    _open_detail(page, live_server_url)
    first_card = page.locator("#candidates-list .clip-card").first
    # First candidate: start=0.0 → "0:00", end=120.0 → "2:00"
    time_btns = first_card.locator(".time-btn")
    expect(time_btns.nth(0)).to_have_text("0:00")
    expect(time_btns.nth(1)).to_have_text("2:00")


def test_candidate_card_shows_category_badge(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Candidate cards display a category badge ('highlight')."""
    _open_detail(page, live_server_url)
    badge = page.locator("#candidates-list .clip-card").first.locator(".badge").first
    expect(badge).to_contain_text("highlight")


def test_candidate_card_shows_confidence_badge(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Candidate cards display a confidence badge (e.g. '90%')."""
    _open_detail(page, live_server_url)
    # Second badge in the clip-meta row is the confidence badge
    badges = page.locator("#candidates-list .clip-card").first.locator(".clip-meta .badge")
    conf_badge = badges.nth(1)
    expect(conf_badge).to_contain_text("%")


def test_candidate_tab_count_label(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The 候補 tab button label shows the count of candidates."""
    _open_detail(page, live_server_url)
    tab_btn = page.locator(".tab-bar button").nth(0)
    expect(tab_btn).to_contain_text("候補 (3)")


# ── AI find button ────────────────────────────────────────────────────────────


def test_ai_find_button_present_and_enabled(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The '🤖 AI でクリップ候補を探す' button is visible and enabled."""
    _open_detail(page, live_server_url)
    btn = page.locator("#find-btn")
    expect(btn).to_be_visible()
    expect(btn).to_be_enabled()
    expect(btn).to_contain_text("AI でクリップ候補を探す")


# ── Approve (採用) button ─────────────────────────────────────────────────────


def test_approve_button_visible(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Each candidate card has a '✔ 採用' button."""
    _open_detail(page, live_server_url)
    approve_btns = page.locator("#candidates-list .btn-approve")
    expect(approve_btns).to_have_count(3)


def test_approve_button_sends_post(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Clicking '✔ 採用' sends an HTMX POST to /api/clips/approve.

    We capture the outgoing request and verify the JSON body contains the
    correct ``candidate_id``.
    """
    _open_detail(page, live_server_url)

    first_card = page.locator("#candidates-list .clip-card").first
    first_cid = first_card.get_attribute("id", ).replace("cand-", "")  # type: ignore[union-attr]

    posted: list[dict] = []

    def _capture(request: Request) -> None:
        if "/api/clips/approve" in request.url and request.method == "POST":
            try:
                posted.append(request.post_data_json or json.loads(request.post_data or "{}"))
            except Exception:
                pass

    page.on("request", _capture)
    first_card.locator(".btn-approve").click()
    page.wait_for_timeout(600)

    assert posted, "No POST request was sent to /api/clips/approve"
    assert any(p.get("candidate_id") == first_cid for p in posted)


# ── Selections tab ────────────────────────────────────────────────────────────


def test_selections_tab_switch(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Clicking 確定 tab shows the selection cards and hides candidate cards."""
    _open_detail(page, live_server_url)
    page.locator(".tab-bar button").nth(1).click()
    page.wait_for_timeout(300)

    # Selection cards become visible
    sel_cards = page.locator(".clip-list").nth(1).locator(".clip-card")
    expect(sel_cards).to_have_count(1)

    # Candidate list is now hidden (Alpine x-show)
    cand_list = page.locator("#candidates-list")
    expect(cand_list).to_be_hidden()


def test_selections_tab_count_label(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The 確定 tab button shows the count of selections."""
    _open_detail(page, live_server_url)
    tab_btn = page.locator(".tab-bar button").nth(1)
    expect(tab_btn).to_contain_text("確定 (1)")


def test_selection_card_has_reject_button(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Selection cards have a '✘ 却下' button."""
    _open_detail(page, live_server_url)
    page.locator(".tab-bar button").nth(1).click()
    page.wait_for_timeout(300)
    reject_btn = page.locator(".clip-list").nth(1).locator(".btn-reject")
    expect(reject_btn).to_be_visible()
    expect(reject_btn).to_contain_text("却下")


# ── Transcript tab ────────────────────────────────────────────────────────────


def test_transcript_tab_fires_htmx_request(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Clicking 文字起こし tab triggers a GET to /htmx/transcript/<video_id>."""
    _open_detail(page, live_server_url)

    htmx_requests: list[str] = []
    page.on(
        "request",
        lambda r: htmx_requests.append(r.url) if "htmx/transcript" in r.url else None,
    )

    page.locator(".tab-bar button").nth(2).click()
    page.wait_for_timeout(600)

    assert any(TEST_VIDEO_ID in url for url in htmx_requests), (
        f"Expected HTMX transcript request for {TEST_VIDEO_ID!r}, got: {htmx_requests}"
    )


def test_transcript_tab_only_fires_once(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The transcript HTMX request is only sent once (hx-trigger='click once')."""
    _open_detail(page, live_server_url)

    htmx_requests: list[str] = []
    page.on(
        "request",
        lambda r: htmx_requests.append(r.url) if "htmx/transcript" in r.url else None,
    )

    transcript_tab = page.locator(".tab-bar button").nth(2)
    transcript_tab.click()
    page.wait_for_timeout(400)
    # Switch away and back
    page.locator(".tab-bar button").nth(0).click()
    page.wait_for_timeout(200)
    transcript_tab.click()
    page.wait_for_timeout(400)

    assert len(htmx_requests) == 1, (
        f"Expected exactly 1 transcript request, got {len(htmx_requests)}"
    )


# ── Clip transcript details ───────────────────────────────────────────────────


def test_candidate_transcript_details_fires_htmx(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Opening the '文字起こし' <details> inside a candidate card fires HTMX."""
    _open_detail(page, live_server_url)

    htmx_requests: list[str] = []
    page.on(
        "request",
        lambda r: htmx_requests.append(r.url) if "htmx/transcript" in r.url else None,
    )

    first_card = page.locator("#candidates-list .clip-card").first
    first_card.locator("details summary").click()
    page.wait_for_timeout(600)

    # Should include start= and end= params
    assert any("start=" in url and "end=" in url for url in htmx_requests), (
        f"Expected transcript with start/end params, got: {htmx_requests}"
    )


# ── Manual clip form ──────────────────────────────────────────────────────────


def test_manual_form_opens_on_details_click(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Clicking '手動でクリップを追加' expands the form."""
    _open_detail(page, live_server_url)
    page.locator("details.manual-add summary").click()
    page.wait_for_timeout(200)
    expect(page.locator(".manual-form")).to_be_visible()


def test_manual_form_has_required_fields(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """The manual form contains start, end, title, and notes inputs."""
    _open_detail(page, live_server_url)
    page.locator("details.manual-add summary").click()
    page.wait_for_timeout(200)
    form = page.locator(".manual-form")
    expect(form.locator("input[name='start']")).to_be_visible()
    expect(form.locator("input[name='end']")).to_be_visible()
    expect(form.locator("input[name='title']")).to_be_visible()
    expect(form.locator("input[name='notes']")).to_be_visible()


def test_manual_form_submit_creates_selection(
    page: Page, live_server_url: str, seeded_clips: dict
) -> None:
    """Filling and submitting the manual form POSTs to /api/clips/create."""
    _open_detail(page, live_server_url)
    page.locator("details.manual-add summary").click()
    page.wait_for_timeout(200)

    form = page.locator(".manual-form")
    form.locator("input[name='start']").fill("10")
    form.locator("input[name='end']").fill("30")
    form.locator("input[name='title']").fill("Manual Test Clip")
    form.locator("input[name='notes']").fill("Added by test")

    posted: list[str] = []
    page.on(
        "request",
        lambda r: posted.append(r.url) if "/api/clips/create" in r.url else None,
    )
    form.locator("button[type='submit']").click()
    page.wait_for_timeout(500)

    assert any("/api/clips/create" in url for url in posted), (
        "Expected POST to /api/clips/create"
    )
