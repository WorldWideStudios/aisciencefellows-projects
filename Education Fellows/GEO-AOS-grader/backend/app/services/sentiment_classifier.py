"""Классификация тональности упоминания бренда в ответе AI-поисковика."""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from app.config import settings
from app.models import Sentiment
from app.services.llm_client import query

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "sentiment_classifier.txt"

_VALID = {"positive", "neutral", "negative"}


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def classify_sentiment(answer_text: str, brand_name: str) -> Sentiment | None:
    """Один вызов LLM. Возвращает Sentiment или None при ошибке/невалидном ответе.

    Вызывать только если brand_mentioned == True (экономия токенов).
    """
    if not answer_text.strip() or not brand_name.strip():
        return None

    system_prompt = _load_system_prompt()
    user_message = f"Бренд: {brand_name}\n\nТекст ответа AI:\n{answer_text}"
    full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    try:
        response = await query(
            prompt=full_prompt,
            model=settings.MODEL_AUX,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.warning("sentiment_classifier: LLM call failed: {}", e)
        return None

    try:
        data = json.loads(response.text.strip())
        value = str(data.get("sentiment", "")).strip().lower()
    except (json.JSONDecodeError, AttributeError):
        logger.warning("sentiment_classifier: invalid JSON: {}", response.text[:200])
        return None

    if value not in _VALID:
        return None
    return Sentiment(value)
