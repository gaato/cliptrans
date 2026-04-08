"""PydanticAI-based translation adapter implementing TranslatorPort."""

from __future__ import annotations

from typing import cast

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model

from cliptrans.domain.errors import TranslateError
from cliptrans.domain.models import Utterance


class _TranslatedItem(BaseModel):
    id: str
    translation: str


class _TranslationResult(BaseModel):
    items: list[_TranslatedItem]


def _model_name(provider: str, model: str) -> str:
    """Map (provider, model) to a PydanticAI model string, e.g. 'openai:gpt-4o'."""
    _PROVIDER_PREFIX = {
        "openai": "openai",
        "anthropic": "anthropic",
        "gemini": "google-gla",
        "google": "google-gla",
    }
    prefix = _PROVIDER_PREFIX.get(provider.lower(), provider.lower())
    return f"{prefix}:{model}"


def _use_openai_responses_model(model: str) -> bool:
    normalized = model.lower()
    return normalized.startswith("gpt-5")


class PydanticAITranslator:
    def __init__(
        self, provider: str = "openai", model: str = "gpt-4o", api_key: str | None = None
    ) -> None:
        self._model_id = _model_name(provider, model)
        self._provider = provider
        self._model = model
        self._api_key = api_key

    def _build_model(self) -> Model:
        """Build a PydanticAI model object with explicit API key if provided."""
        provider = self._provider.lower()
        api_key = self._api_key
        if provider == "openai":
            from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
            from pydantic_ai.providers.openai import OpenAIProvider

            model_cls = (
                OpenAIResponsesModel
                if _use_openai_responses_model(self._model)
                else OpenAIChatModel
            )
            return model_cls(self._model, provider=OpenAIProvider(api_key=api_key))
        if provider == "anthropic":
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider

            return AnthropicModel(self._model, provider=AnthropicProvider(api_key=api_key))
        if provider in ("gemini", "google-gla", "google"):
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            return GoogleModel(self._model, provider=GoogleProvider(api_key=api_key))
        raise ValueError(f"Unsupported LLM provider: {self._provider!r}")

    async def translate(
        self,
        utterances: list[Utterance],
        *,
        source_lang: str,
        target_lang: str,
        glossary: dict[str, str] | None = None,
        context: list[Utterance] | None = None,
    ) -> list[Utterance]:
        if not utterances:
            return utterances

        glossary_text = ""
        if glossary:
            lines = "\n".join(f"  {k} → {t}" for k, t in glossary.items())
            glossary_text = f"\nGlossary (use these exact terms):\n{lines}"

        context_text = ""
        if context:
            recent = "\n".join(
                f"  [{u.original}] → [{u.translation or '(untranslated)'}]" for u in context[-5:]
            )
            context_text = f"\nPrevious utterances for context:\n{recent}"

        system_prompt = (
            f"You translate subtitle utterances from {source_lang} to {target_lang}. "
            "Return a JSON object with an 'items' array where each element has 'id' "
            "(the original utterance id) and 'translation' (the translated text). "
            "Preserve timing, speaker tone, and naturalness. "
            "Do NOT translate IDs."
            f"{glossary_text}"
            f"{context_text}"
        )

        user_lines = "\n".join(f'id={u.id} text="{u.original}"' for u in utterances)

        model_obj = self._build_model()
        agent = Agent(model_obj, output_type=_TranslationResult, system_prompt=system_prompt)

        try:
            result = await agent.run(user_lines)
        except Exception as exc:
            raise TranslateError(f"LLM translation failed: {exc}") from exc

        translation_map = {
            item.id: item.translation for item in cast(_TranslationResult, result.output).items
        }

        updated: list[Utterance] = []
        for utt in utterances:
            translated_text = translation_map.get(str(utt.id))
            updated.append(utt.model_copy(update={"translation": translated_text}))
        return updated
