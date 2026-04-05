from typing import Protocol

from cliptrans.domain.models import Utterance


class TranslatorPort(Protocol):
    async def translate(
        self,
        utterances: list[Utterance],
        *,
        source_lang: str,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        context: list[Utterance] | None = None,
    ) -> list[Utterance]: ...
