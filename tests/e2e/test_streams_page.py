"""E2E tests for the stream list page (/).

Covers
------
* Page loads with correct title
* Stream cards are rendered from mock Holodex data
* Clicking a card navigates to the stream detail page
* Org / status URL filters work
* Channel autocomplete (Alpine.js + fetch)
  - Partial typing triggers the suggest API (server-side mock)
  - Selecting a suggestion navigates with the channel_id query param
  - ``page.route()`` can override the server response for edge-case tests
    (no-results, API error graceful degradation)
"""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import Page, Route, expect

from e2e.fixtures import KIARA_CHANNEL_ID, KIARA_STREAM, TEST_VIDEO_ID

pytestmark = pytest.mark.e2e


# ── Helpers ───────────────────────────────────────────────────────────────────


def _goto(page: Page, live_server_url: str, path: str = "/") -> None:
    page.goto(live_server_url + path)
    page.wait_for_load_state("networkidle")
    # Allow Alpine.js time to initialise (it's loaded from CDN)
    page.wait_for_timeout(800)


# ── Basic page load ───────────────────────────────────────────────────────────


def test_page_title(page: Page, live_server_url: str) -> None:
    """The streams page has the expected <title>."""
    _goto(page, live_server_url)
    expect(page).to_have_title("Streams — ClipTrans")


def test_navigation_links(page: Page, live_server_url: str) -> None:
    """The nav contains links to Streams and Selections."""
    _goto(page, live_server_url)
    nav = page.locator("nav")
    expect(nav.get_by_role("link", name="Streams")).to_be_visible()
    expect(nav.get_by_role("link", name="Selections")).to_be_visible()


# ── Stream cards ──────────────────────────────────────────────────────────────


def test_stream_cards_rendered(page: Page, live_server_url: str) -> None:
    """MockHolodex returns KIARA_STREAM; the card should appear on the page."""
    _goto(page, live_server_url)
    card = page.locator(".stream-card").first
    expect(card).to_be_visible()
    # Title text appears somewhere in the card
    expect(page.locator(".stream-title").first).to_contain_text(KIARA_STREAM.title)


def test_stream_card_shows_channel_and_org(page: Page, live_server_url: str) -> None:
    """Stream card displays channel name and org."""
    _goto(page, live_server_url)
    card = page.locator(".stream-card").first
    expect(card).to_contain_text("Takanashi Kiara")
    expect(card).to_contain_text("Hololive")


def test_stream_card_shows_duration(page: Page, live_server_url: str) -> None:
    """Stream card shows human-readable duration (2h 2m for 7320 seconds)."""
    _goto(page, live_server_url)
    duration = page.locator(".stream-duration").first
    expect(duration).to_contain_text("2h")
    expect(duration).to_contain_text("2m")


def test_stream_card_links_to_detail(page: Page, live_server_url: str) -> None:
    """Clicking a stream card navigates to /stream/<video_id>."""
    _goto(page, live_server_url)
    page.locator(".stream-card").first.click()
    page.wait_for_load_state("networkidle")
    assert f"/stream/{TEST_VIDEO_ID}" in page.url


# ── Filter form ───────────────────────────────────────────────────────────────


def test_filter_form_elements_visible(page: Page, live_server_url: str) -> None:
    """Channel input, org input, status select, and submit button are visible."""
    _goto(page, live_server_url)
    expect(page.get_by_placeholder("キアラ / Kobo …")).to_be_visible()
    expect(page.get_by_placeholder("Hololive …")).to_be_visible()
    expect(page.get_by_role("combobox", name="Status")).to_be_visible()
    expect(page.get_by_role("button", name="検索")).to_be_visible()


def test_org_filter_appends_to_url(page: Page, live_server_url: str) -> None:
    """Typing an org and submitting updates the URL with ?org=."""
    _goto(page, live_server_url)
    page.get_by_placeholder("Hololive …").fill("Hololive")
    page.get_by_role("button", name="検索").click()
    page.wait_for_load_state("networkidle")
    assert "org=Hololive" in page.url


def test_status_live_filter(page: Page, live_server_url: str) -> None:
    """Selecting 'Live' status and submitting adds ?status=live to the URL."""
    _goto(page, live_server_url)
    page.get_by_role("combobox", name="Status").select_option("live")
    page.get_by_role("button", name="検索").click()
    page.wait_for_load_state("networkidle")
    assert "status=live" in page.url


def test_status_defaults_to_past(page: Page, live_server_url: str) -> None:
    """The status select defaults to 'past' on first load."""
    _goto(page, live_server_url)
    select = page.get_by_role("combobox", name="Status")
    assert select.input_value() == "past"


# ── Channel autocomplete ──────────────────────────────────────────────────────
#
# Design note
# -----------
# The autocomplete calls GET /api/streams/channels/suggest?q=<query>.
# In these tests that endpoint is served by the live server whose Holodex
# dependency is already overridden with MockHolodex.  MockHolodex returns
# KIARA_CHANNEL for any query containing "kiara" or "takanashi".
#
# page.route() is used only in the last two tests to demonstrate how to
# override the suggest response independently of the server mock.


def test_channel_autocomplete_appears_on_partial_input(
    page: Page, live_server_url: str
) -> None:
    """Typing a partial name ('kiar') shows the suggestion dropdown."""
    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("kiar", delay=50)
    # Wait for Alpine debounce (300 ms) + fetch + DOM update
    page.wait_for_timeout(600)
    suggestions = page.locator(".channel-suggestions")
    expect(suggestions).to_be_visible()
    expect(suggestions).to_contain_text("Takanashi Kiara")


def test_channel_autocomplete_full_name(page: Page, live_server_url: str) -> None:
    """Typing the full name 'takanashi kiara' shows the suggestion."""
    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    # Type one character at a time to trigger debounce correctly
    inp.type("takanashi kiara", delay=50)
    page.wait_for_timeout(600)
    expect(page.locator(".channel-suggestions")).to_contain_text("Takanashi Kiara")
    expect(page.locator(".channel-suggestions")).to_contain_text("Hololive")


def test_channel_autocomplete_no_results_for_unknown_query(
    page: Page, live_server_url: str
) -> None:
    """An unknown query returns no suggestions; the dropdown stays hidden."""
    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("zzzzxxx", delay=50)
    page.wait_for_timeout(600)
    # x-show="suggestions.length" — dropdown is hidden (display:none or absent)
    suggestions = page.locator(".channel-suggestions")
    expect(suggestions).to_be_hidden()


def test_channel_autocomplete_select_navigates(page: Page, live_server_url: str) -> None:
    """Selecting a suggestion from the dropdown navigates to /?channel_id=…."""
    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("kiara", delay=50)
    page.wait_for_timeout(600)

    # Click the first suggestion button
    page.locator(".suggestion-item").first.click()
    page.wait_for_load_state("networkidle")

    assert f"channel_id={KIARA_CHANNEL_ID}" in page.url
    assert "channel_name=Takanashi+Kiara" in page.url or "channel_name=Takanashi%20Kiara" in page.url


def test_channel_autocomplete_shows_selected_label(page: Page, live_server_url: str) -> None:
    """After selection the text input hides and the selected label appears."""
    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("kiara", delay=50)
    page.wait_for_timeout(600)
    page.locator(".suggestion-item").first.click()
    page.wait_for_load_state("networkidle")

    # After navigating back, channel_name is in the URL so Alpine re-renders
    # the selected state
    selected = page.locator(".channel-selected")
    expect(selected).to_be_visible()
    expect(selected).to_contain_text("Takanashi Kiara")


def test_channel_autocomplete_clear_button(page: Page, live_server_url: str) -> None:
    """The ✕ button in the selected state clears the selection."""
    # Navigate with a pre-selected channel
    _goto(
        page,
        live_server_url,
        f"/?channel_id={KIARA_CHANNEL_ID}&channel_name=Takanashi+Kiara&status=past",
    )
    page.wait_for_timeout(800)

    # The selected state should be visible
    selected = page.locator(".channel-selected")
    expect(selected).to_be_visible()

    # Click the clear button
    page.locator(".clear-btn").click()
    page.wait_for_timeout(300)

    # The text input should appear again
    expect(page.get_by_placeholder("キアラ / Kobo …")).to_be_visible()
    expect(selected).to_be_hidden()


def test_channel_autocomplete_escape_clears_suggestions(
    page: Page, live_server_url: str
) -> None:
    """Pressing Escape hides the suggestions without selecting."""
    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("kiara", delay=50)
    page.wait_for_timeout(600)
    expect(page.locator(".channel-suggestions")).to_be_visible()

    inp.press("Escape")
    page.wait_for_timeout(200)
    expect(page.locator(".channel-suggestions")).to_be_hidden()


# ── page.route() — browser-level request interception ────────────────────────
#
# These tests show how to override the suggest endpoint at the browser level
# so tests remain fully self-contained even without a running server.


def test_channel_autocomplete_via_page_route(page: Page, live_server_url: str) -> None:
    """page.route() intercepts /api/streams/channels/suggest and injects data.

    This technique is useful when you want deterministic fixture data that is
    independent of the server's mock implementation.
    """
    kiara_payload = json.dumps([
        {
            "id": KIARA_CHANNEL_ID,
            "name": "Takanashi Kiara Ch. hololive-EN",
            "english_name": "Takanashi Kiara",
            "photo": "",
            "org": "Hololive",
        }
    ])

    def _intercept(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=kiara_payload,
        )

    page.route(re.compile(r"/api/streams/channels/suggest"), _intercept)

    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("kiara", delay=50)
    page.wait_for_timeout(600)

    expect(page.locator(".channel-suggestions")).to_contain_text("Takanashi Kiara")


def test_channel_autocomplete_api_error_is_silent(
    page: Page, live_server_url: str
) -> None:
    """If the suggest API returns 500, the UI shows no suggestions (no crash)."""

    def _error(route: Route) -> None:
        route.fulfill(status=500, body="Internal Server Error")

    page.route(re.compile(r"/api/streams/channels/suggest"), _error)

    _goto(page, live_server_url)
    inp = page.get_by_placeholder("キアラ / Kobo …")
    inp.click()
    inp.type("kiara", delay=50)
    page.wait_for_timeout(600)

    # No suggestions should appear; the page should not crash
    expect(page.locator(".channel-suggestions")).to_be_hidden()
    # The page itself must still be functional
    expect(page.get_by_role("button", name="検索")).to_be_visible()
