from __future__ import annotations

from cliptrans.adapters.llm.clip_finder_agent import _build_system_prompt


def test_clip_finder_prompt_uses_requested_language() -> None:
    prompt = _build_system_prompt("ja-JP")

    assert "user's language (ja-JP)" in prompt
    assert "title: short clip title" in prompt
    assert "reason: one sentence" in prompt
