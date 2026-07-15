"""Сопоставление списка URL-источников с доменом бренда и доменами конкурентов."""
from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse


def normalize_domain(value: str) -> str:
    """Привести домен или URL к каноническому виду: lowercase, без www, без пути."""
    value = value.strip().lower()
    if "://" in value:
        host = urlparse(value).netloc
    else:
        host = value.split("/", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def domain_matches(target: str, candidate: str) -> bool:
    """True, если candidate совпадает с target или является его поддоменом.

    `blog.tinkoff.ru` совпадает с `tinkoff.ru`, но не с `kontur.ru`.
    """
    if not target or not candidate:
        return False
    return candidate == target or candidate.endswith("." + target)


def match_citations(
    urls: Iterable[str],
    brand_domain: str,
    competitor_domains: list[str],
) -> dict:
    brand_target = normalize_domain(brand_domain) if brand_domain else ""
    competitor_targets = [normalize_domain(d) for d in competitor_domains if d]

    all_domains: list[str] = []
    brand_cited = False
    competitors_cited: list[str] = []
    seen_competitors: set[str] = set()

    for url in urls:
        if not isinstance(url, str) or not url.strip():
            continue
        domain = normalize_domain(url)
        if not domain:
            continue
        all_domains.append(domain)
        if brand_target and domain_matches(brand_target, domain):
            brand_cited = True
        for ct in competitor_targets:
            if domain_matches(ct, domain) and ct not in seen_competitors:
                competitors_cited.append(ct)
                seen_competitors.add(ct)

    return {
        "brand_cited": brand_cited,
        "competitors_cited": competitors_cited,
        "all_cited_domains": all_domains,
    }
