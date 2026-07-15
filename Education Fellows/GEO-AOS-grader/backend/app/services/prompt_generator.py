"""Генерация 10 поисковых запросов под профиль бренда."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import settings
from app.services.llm_client import query

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "prompt_generator.txt"


class PromptGeneratorError(Exception):
    pass


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_user_message(brand: dict[str, Any]) -> str:
    competitor_lines = [
        f"  - {c['name']} ({c['domain']})" for c in brand.get("competitors", [])
    ]
    return (
        f"Бренд: {brand['brand_name']}\n"
        f"Отрасль: {brand.get('industry', '')}\n"
        f"Описание: {brand.get('brand_description', '')}\n"
        f"Конкуренты:\n" + ("\n".join(competitor_lines) if competitor_lines else "  (не указаны)")
    )


async def generate_prompts(brand: dict[str, Any]) -> list[str]:
    system_prompt = _load_system_prompt()
    user_message = _build_user_message(brand)
    full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    response = await query(
        prompt=full_prompt,
        model=settings.MODEL_AUX,
        response_format={"type": "json_object"},
    )

    text = response.text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("prompt_generator: invalid JSON from LLM: {}", text[:500])
        raise PromptGeneratorError(f"LLM returned non-JSON: {e}") from e

    prompts = data.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise PromptGeneratorError("LLM response missing 'prompts' array")

    cleaned = [str(p).strip() for p in prompts if str(p).strip()]
    if len(cleaned) < 5:
        raise PromptGeneratorError(f"Got only {len(cleaned)} usable prompts")

    return cleaned[:10]
