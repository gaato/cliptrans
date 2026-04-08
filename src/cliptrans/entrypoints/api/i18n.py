"""Helpers for deriving user-facing language preferences from HTTP requests."""

from __future__ import annotations

from fastapi import Request

_DEFAULT_LANGUAGE = "en"


def preferred_language(request: Request) -> str:
    """Return the best-effort user language from Accept-Language."""
    header = request.headers.get("accept-language", "")
    if not header:
        return _DEFAULT_LANGUAGE

    weighted: list[tuple[float, str]] = []
    for item in header.split(","):
        raw = item.strip()
        if not raw:
            continue
        lang, _, params = raw.partition(";")
        lang = lang.strip().replace("_", "-")
        if not lang or lang == "*":
            continue
        quality = 1.0
        if params:
            for param in params.split(";"):
                key, _, value = param.strip().partition("=")
                if key == "q":
                    try:
                        quality = float(value)
                    except ValueError:
                        quality = 0.0
        weighted.append((quality, lang))

    if not weighted:
        return _DEFAULT_LANGUAGE

    weighted.sort(key=lambda item: item[0], reverse=True)
    return weighted[0][1]
