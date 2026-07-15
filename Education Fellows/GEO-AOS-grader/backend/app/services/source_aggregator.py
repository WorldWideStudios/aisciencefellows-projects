"""Агрегация Source Share of Voice: топ-15 доменов из всех ответов."""
from __future__ import annotations

from collections import Counter

from app.services.citation_matcher import domain_matches, normalize_domain

TOP_N = 15


def aggregate_sources(
    all_citation_lists: list[list[str]],
    brand_domain: str,
    competitor_domains: list[str],
) -> list[dict]:
    brand_target = normalize_domain(brand_domain) if brand_domain else ""
    competitor_targets = [normalize_domain(d) for d in competitor_domains if d]

    counter: Counter[str] = Counter()
    for citations in all_citation_lists:
        for d in citations:
            if isinstance(d, str) and d:
                counter[normalize_domain(d)] += 1

    result: list[dict] = []
    for domain, count in counter.most_common(TOP_N):
        is_brand = bool(brand_target) and domain_matches(brand_target, domain)
        is_competitor = any(domain_matches(ct, domain) for ct in competitor_targets)
        result.append(
            {
                "domain": domain,
                "count": count,
                "is_brand": is_brand,
                "is_competitor": is_competitor and not is_brand,
            }
        )
    return result
