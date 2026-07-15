"""Парсер сайта: главная + до 3 ключевых подстраниц."""
from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 10.0
MAX_TOTAL_CHARS = 10_000
SUBPAGE_KEYWORDS = (
    "about", "о-нас", "o-nas", "услуги", "uslugi", "продукты", "produkty",
    "services", "products", "company", "kompaniya", "о-компании",
)


class SiteParseError(Exception):
    """Сайт не удалось обработать (недоступен / нет контента)."""


def _extract_visible_text(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(" ", strip=True)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _find_subpage_links(soup: BeautifulSoup, base_url: str, limit: int = 3) -> list[str]:
    base_host = urlparse(base_url).netloc
    seen: set[str] = set()
    candidates: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc and parsed.netloc != base_host:
            continue
        path_lower = parsed.path.lower()
        if not any(kw in path_lower for kw in SUBPAGE_KEYWORDS):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        candidates.append(absolute)
        if len(candidates) >= limit:
            break

    return candidates


async def _fetch(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        resp = await client.get(url, timeout=REQUEST_TIMEOUT)
    except (httpx.TimeoutException, httpx.TransportError) as e:
        logger.warning("site_parser: fetch failed {}: {}", url, e)
        return None
    if resp.status_code >= 400:
        logger.warning("site_parser: {} returned {}", url, resp.status_code)
        return None
    return resp.content


async def parse_site(url: str) -> dict[str, Any]:
    """Скачать главную + до 3 подстраниц, собрать видимый текст.

    Возвращает: {home_text, sub_pages, meta, url}. Общий объём текста до 10k символов.
    Кидает SiteParseError, если главная недоступна или нет контента.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        home_bytes = await _fetch(client, url)
        if home_bytes is None:
            raise SiteParseError("Не удалось загрузить сайт")

        soup = BeautifulSoup(home_bytes, "lxml")
        title = (soup.title.string if soup.title and soup.title.string else "").strip()
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()

        home_text = _extract_visible_text(soup)
        if len(home_text) < 200 and not title and not description:
            raise SiteParseError("Сайт не содержит достаточно контента для анализа")

        subpage_urls = _find_subpage_links(soup, url, limit=3)
        sub_pages_text: list[str] = []
        if subpage_urls:
            sub_htmls = await asyncio.gather(*(_fetch(client, u) for u in subpage_urls))
            for sub_url, sub_html in zip(subpage_urls, sub_htmls):
                if not sub_html:
                    continue
                sub_soup = BeautifulSoup(sub_html, "lxml")  # bytes → BS detects encoding
                sub_text = _extract_visible_text(sub_soup)
                if sub_text:
                    sub_pages_text.append(f"# {sub_url}\n{sub_text}")

    combined = "\n\n".join([f"# {url}\n{home_text}", *sub_pages_text])
    combined = re.sub(r"\n{3,}", "\n\n", combined)
    if len(combined) > MAX_TOTAL_CHARS:
        combined = combined[:MAX_TOTAL_CHARS]

    return {
        "url": url,
        "home_text": home_text,
        "sub_pages": sub_pages_text,
        "combined_text": combined,
        "meta": {"title": title, "description": description},
    }
