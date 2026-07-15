"""Единый асинхронный клиент к OpenRouter (OpenAI-совместимый API).

Один клиент на всё приложение. Модель передаётся параметром.
Никаких отдельных perplexity_client / openai_client.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from app.config import settings


@dataclass
class LLMResponse:
    text: str
    citations: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClientError(Exception):
    pass


def _extract_text(payload: dict[str, Any]) -> str:
    try:
        return payload["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _extract_citations(payload: dict[str, Any]) -> list[str]:
    """Citations от Perplexity могут лежать в двух местах:

    1. корневое поле `citations` — массив URL
    2. choices[0].message.annotations — массив объектов с url_citation.url
    """
    urls: list[str] = []
    seen: set[str] = set()

    root = payload.get("citations")
    if isinstance(root, list):
        for item in root:
            if isinstance(item, str) and item not in seen:
                urls.append(item)
                seen.add(item)
            elif isinstance(item, dict):
                url = item.get("url") or item.get("href")
                if isinstance(url, str) and url not in seen:
                    urls.append(url)
                    seen.add(url)

    try:
        annotations = payload["choices"][0]["message"].get("annotations") or []
    except (KeyError, IndexError, TypeError):
        annotations = []

    for ann in annotations:
        if not isinstance(ann, dict):
            continue
        url = None
        if isinstance(ann.get("url_citation"), dict):
            url = ann["url_citation"].get("url")
        url = url or ann.get("url")
        if isinstance(url, str) and url not in seen:
            urls.append(url)
            seen.add(url)

    return urls


async def query(
    prompt: str,
    model: str,
    response_format: dict | None = None,
    timeout: float = 30.0,
) -> LLMResponse:
    if not settings.OPENROUTER_API_KEY:
        raise LLMClientError("OPENROUTER_API_KEY is not set")

    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if response_format is not None:
        body["response_format"] = response_format

    backoff = 1.5
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=body)

            if resp.status_code >= 500:
                raise LLMClientError(f"OpenRouter {resp.status_code}: {resp.text[:300]}")
            if resp.status_code in (401, 403):
                logger.error("OpenRouter auth failed ({}): check OPENROUTER_API_KEY", resp.status_code)
                raise LLMClientError(f"OpenRouter auth error {resp.status_code}")
            if resp.status_code >= 400:
                raise LLMClientError(f"OpenRouter {resp.status_code}: {resp.text[:300]}")

            payload = resp.json()
            return LLMResponse(
                text=_extract_text(payload),
                citations=_extract_citations(payload),
                raw=payload,
            )
        except (httpx.TimeoutException, httpx.TransportError, LLMClientError) as e:
            last_error = e
            if attempt == 0:
                logger.warning("OpenRouter call failed (attempt 1/2): {}. Retrying in {}s", e, backoff)
                await asyncio.sleep(backoff)
                continue
            logger.error("OpenRouter call failed (attempt 2/2): {}", e)
            raise

    assert last_error is not None
    raise last_error
