"""LLM-анализ собранного текста сайта → структурированные данные о бренде."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import settings
from app.services.llm_client import query

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "brand_analyzer.txt"


class BrandAnalyzerError(Exception):
    pass


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_user_message(site_data: dict[str, Any]) -> str:
    meta = site_data.get("meta") or {}
    parts = [
        f"URL: {site_data['url']}",
        f"Title: {meta.get('title', '')}",
        f"Description: {meta.get('description', '')}",
        "",
        "Текст сайта:",
        site_data.get("combined_text", ""),
    ]
    return "\n".join(parts)


async def analyze_brand(site_data: dict[str, Any]) -> dict[str, Any]:
    system_prompt = _load_system_prompt()
    user_message = _build_user_message(site_data)
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
        logger.error("brand_analyzer: invalid JSON from LLM: {}", text[:500])
        raise BrandAnalyzerError(f"LLM returned non-JSON: {e}") from e

    for key in ("brand_name", "brand_domain", "brand_aliases", "brand_description", "industry", "competitors"):
        if key not in data:
            raise BrandAnalyzerError(f"LLM response missing field: {key}")

    if not isinstance(data["brand_aliases"], list):
        data["brand_aliases"] = [data["brand_name"]]
    if not isinstance(data["competitors"], list):
        data["competitors"] = []

    competitors_clean = []
    for c in data["competitors"]:
        if isinstance(c, dict) and c.get("name") and c.get("domain"):
            competitors_clean.append({"name": str(c["name"]), "domain": str(c["domain"]).lower()})
    data["competitors"] = competitors_clean[:5]

    data["brand_domain"] = str(data["brand_domain"]).lower().lstrip("www.")
    return data
