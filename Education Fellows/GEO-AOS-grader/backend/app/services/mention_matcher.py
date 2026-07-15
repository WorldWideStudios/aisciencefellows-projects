"""Поиск упоминаний бренда и конкурентов в тексте ответа Perplexity.

`\\b` в стандартном re плохо работает с кириллицей (он считает букву из не-ASCII
не "word character" в зависимости от флагов). Поэтому используем явный
lookbehind/lookahead с `[\\W_]` или начало/конец строки.
"""
from __future__ import annotations

import re
from typing import Iterable


def _make_boundary_pattern(alias: str) -> re.Pattern[str]:
    """Regex с word boundary, безопасный для кириллицы.

    Левая граница строгая (start-of-text или не-буква) — защищает от частичных
    совпадений в середине слова. Правая граница ослаблена: после alias можно
    дописать до 4 букв — это покрывает русские склонения ("Альфа-Банка", "Тинькоффу"),
    но не пропускает совсем другие слова.
    """
    escaped = re.escape(alias.strip())
    pattern = rf"(?:(?<=^)|(?<=[\W_])){escaped}[\w]{{0,4}}(?=$|[\W_])"
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)


def find_mentions(text: str, terms: Iterable[str]) -> list[str]:
    """Вернёт список терминов (в исходной форме), найденных в тексте."""
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for term in terms:
        term = (term or "").strip()
        if not term or term in seen:
            continue
        if _make_boundary_pattern(term).search(text):
            found.append(term)
            seen.add(term)
    return found


def match_mentions(
    text: str,
    brand_aliases: list[str],
    competitor_names: list[str],
) -> dict:
    brand_hits = find_mentions(text, brand_aliases)
    competitor_hits = find_mentions(text, competitor_names)
    return {
        "brand_mentioned": bool(brand_hits),
        "brand_mention_terms": brand_hits,
        "competitors_mentioned": competitor_hits,
    }
