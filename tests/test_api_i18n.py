from __future__ import annotations

from starlette.requests import Request

from cliptrans.entrypoints.api.i18n import preferred_language


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def test_preferred_language_uses_highest_quality_value() -> None:
    request = _request_with_headers(
        {"Accept-Language": "en-US;q=0.7, ja-JP;q=0.9, fr;q=0.4"}
    )

    assert preferred_language(request) == "ja-JP"


def test_preferred_language_defaults_to_english() -> None:
    request = _request_with_headers({})

    assert preferred_language(request) == "en"


def test_preferred_language_ignores_wildcard_values() -> None:
    request = _request_with_headers({"Accept-Language": "*, en-GB;q=0.8"})

    assert preferred_language(request) == "en-GB"
