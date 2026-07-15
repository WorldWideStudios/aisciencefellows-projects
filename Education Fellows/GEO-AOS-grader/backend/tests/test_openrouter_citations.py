"""Критическая проверка дня 1: Perplexity Sonar Pro через OpenRouter
должна возвращать массив citations. Если эта проверка падает —
продукт не работает, и нужно искать обходной путь.

Запуск (внутри контейнера backend):
    docker compose exec backend pytest tests/test_openrouter_citations.py -s
"""
from __future__ import annotations

import asyncio
import os

import pytest

from app.config import settings
from app.services.llm_client import query


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY") and not settings.OPENROUTER_API_KEY,
    reason="OPENROUTER_API_KEY is not set",
)
def test_perplexity_returns_citations() -> None:
    prompt = "Лучшие онлайн-банки в России 2025"

    response = asyncio.run(query(prompt=prompt, model=settings.MODEL_MAIN))

    print("\n=========== OpenRouter / Perplexity raw probe ===========")
    print(f"Model:         {settings.MODEL_MAIN}")
    print(f"Prompt:        {prompt!r}")
    print(f"Text length:   {len(response.text)} chars")
    print(f"Text preview:  {response.text[:200]!r}")
    print(f"Citations:     {len(response.citations)} URLs")

    raw = response.raw
    root_citations = raw.get("citations")
    try:
        annotations = raw["choices"][0]["message"].get("annotations") or []
    except (KeyError, IndexError, TypeError):
        annotations = []

    in_root = isinstance(root_citations, list) and len(root_citations) > 0
    in_annotations = len(annotations) > 0
    source_label = []
    if in_root:
        source_label.append(f"root.citations[{len(root_citations)}]")
    if in_annotations:
        source_label.append(f"choices[0].message.annotations[{len(annotations)}]")
    print(f"Citations source: {' + '.join(source_label) if source_label else 'NONE'}")

    for idx, url in enumerate(response.citations[:5], start=1):
        print(f"  {idx}. {url}")

    print("=========================================================\n")

    assert response.text, "Perplexity returned empty text"
    assert response.citations, (
        "Perplexity returned no citations — product is non-functional. "
        "Need a workaround (extra_body, direct Perplexity API, etc.)."
    )
