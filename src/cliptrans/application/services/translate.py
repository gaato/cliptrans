"""TranslateService — translate utterances in batches via TranslatorPort."""

from __future__ import annotations

from cliptrans.application.ports.translator import TranslatorPort
from cliptrans.domain.models import Job, Timeline, TranslationMeta
from cliptrans.timeline_io import write_timeline


class TranslateService:
    def __init__(
        self,
        translator: TranslatorPort,
        chunk_size: int = 10,
        context_size: int = 3,
        default_glossary: dict[str, str] | None = None,
    ) -> None:
        self._translator = translator
        self._chunk_size = chunk_size
        self._context_size = context_size
        self._default_glossary: dict[str, str] = default_glossary or {}

    async def execute(self, job: Job, timeline: Timeline) -> Timeline:
        """Translate all utterances in timeline and persist results."""
        assert job.data_dir is not None
        cfg = job.config

        # Merge: config glossary (base) + timeline glossary (job-specific override)
        glossary: dict[str, str] = dict(self._default_glossary)
        if timeline.translation:
            glossary.update(timeline.translation.glossary)

        utterances = list(timeline.utterances)
        translated: list = []

        for i in range(0, len(utterances), self._chunk_size):
            chunk = utterances[i : i + self._chunk_size]
            context = translated[-self._context_size:] if translated else None

            chunk_translated = await self._translator.translate(
                chunk,
                source_lang=cfg.source_language,
                target_lang=cfg.target_language,
                glossary=glossary or None,
                context=context,
            )
            translated.extend(chunk_translated)

        timeline.utterances = translated
        timeline.translation = TranslationMeta(
            provider=getattr(self._translator, "_provider", "unknown"),
            model=getattr(self._translator, "_model", "unknown"),
            source_language=cfg.source_language,
            target_language=cfg.target_language,
            glossary=glossary,
        )

        write_timeline(timeline, job.data_dir / "timeline.json")
        return timeline
