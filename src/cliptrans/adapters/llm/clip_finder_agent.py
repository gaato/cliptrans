"""PydanticAI-based clip finder agent.

Given a chunk of SRT subtitle text, the agent returns a list of ClipCandidate
suggestions with timestamps, category, and confidence.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from cliptrans.domain.errors import ClipFinderError
from cliptrans.domain.models import ClipCandidate


class _RawCandidate(BaseModel):
    start_time: str  # "HH:MM:SS,mmm"
    end_time: str
    title: str
    reason: str
    category: str
    confidence: float


class _FindResult(BaseModel):
    candidates: list[_RawCandidate]


def _srt_to_seconds(ts: str) -> float:
    """Convert SRT timestamp string to seconds."""
    # Support both HH:MM:SS,mmm and HH:MM:SS.mmm
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    raise ValueError(f"Invalid SRT timestamp: {ts}")


def _build_system_prompt(output_language: str) -> str:
    return f"""\
You are an expert video clip curator. Given a transcript (SRT format) of a live stream,
identify the most interesting moments worth clipping. For each candidate:
- start_time / end_time: use exact SRT timestamps from the transcript
- title: short clip title in the user's language ({output_language}) under 25 characters
- reason: one sentence in the user's language ({output_language}) explaining why it is interesting
- category: one of "funny", "emotional", "collab", "music", "controversy", "highlight"
- confidence: 0.0–1.0

Output only JSON matching the schema. Do not fabricate timestamps.
"""


class ClipFinderAgent:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_key: str | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._agents: dict[str, Agent[None, _FindResult]] = {}

    def _build_agent(self, output_language: str) -> Agent[None, _FindResult]:
        from cliptrans.adapters.llm.translation_agent import PydanticAITranslator

        # Reuse the same _build_model logic from PydanticAITranslator
        translator = PydanticAITranslator(self._provider, self._model, self._api_key)
        model_obj = translator._build_model()
        return Agent(  # type: ignore[return-value]  # ty: ignore[invalid-return-type]
            model_obj,
            output_type=_FindResult,
            system_prompt=_build_system_prompt(output_language),
        )

    async def find_candidates(
        self,
        video_id: str,
        srt_chunk: str,
        chunk_offset: float = 0.0,
        output_language: str = "en",
    ) -> list[ClipCandidate]:
        language = output_language or "en"
        agent = self._agents.get(language)
        if agent is None:
            agent = self._build_agent(language)
            self._agents[language] = agent
        try:
            result = await agent.run(srt_chunk)
        except Exception as exc:
            raise ClipFinderError(f"LLM clip finding failed: {exc}") from exc

        candidates: list[ClipCandidate] = []
        for raw in result.output.candidates:
            try:
                start = _srt_to_seconds(raw.start_time) + chunk_offset
                end = _srt_to_seconds(raw.end_time) + chunk_offset
            except ValueError:
                continue
            candidates.append(
                ClipCandidate(
                    stream_id=video_id,
                    start=start,
                    end=end,
                    title=raw.title,
                    reason=raw.reason,
                    category=raw.category,
                    confidence=raw.confidence,
                )
            )
        return candidates
