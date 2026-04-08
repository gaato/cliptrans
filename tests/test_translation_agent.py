from __future__ import annotations

from unittest.mock import patch

from cliptrans.adapters.llm.translation_agent import (
    PydanticAITranslator,
    _use_openai_responses_model,
)


def test_openai_gpt5_models_use_responses_api() -> None:
    assert _use_openai_responses_model("gpt-5.4-mini") is True


def test_openai_gpt4_models_keep_chat_api() -> None:
    assert _use_openai_responses_model("gpt-4o") is False


def test_build_model_uses_openai_responses_model_for_gpt5() -> None:
    translator = PydanticAITranslator(provider="openai", model="gpt-5.4-mini", api_key="test-key")

    with (
        patch("pydantic_ai.models.openai.OpenAIResponsesModel") as responses_model,
        patch("pydantic_ai.models.openai.OpenAIChatModel") as chat_model,
    ):
        translator._build_model()

    responses_model.assert_called_once()
    chat_model.assert_not_called()


def test_build_model_uses_openai_chat_model_for_gpt4() -> None:
    translator = PydanticAITranslator(provider="openai", model="gpt-4o", api_key="test-key")

    with (
        patch("pydantic_ai.models.openai.OpenAIResponsesModel") as responses_model,
        patch("pydantic_ai.models.openai.OpenAIChatModel") as chat_model,
    ):
        translator._build_model()

    chat_model.assert_called_once()
    responses_model.assert_not_called()
