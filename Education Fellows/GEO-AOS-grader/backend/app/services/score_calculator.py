"""Расчёт агрегированных метрик отчёта и финального AEO Score."""
from __future__ import annotations

from app.models import SentimentSummary


def calculate_aeo_score(
    citation_rate: float,
    mention_rate: float,
    sentiment_summary: str,
) -> float:
    base = (citation_rate * 0.6 + mention_rate * 0.4) * 100
    if sentiment_summary == "negative":
        penalty = 0.7
    elif sentiment_summary == "mixed":
        penalty = 0.85
    else:
        penalty = 1.0
    return round(base * penalty, 1)


def determine_sentiment_summary(sentiments: list[str]) -> SentimentSummary:
    has_neg = "negative" in sentiments
    has_pos = "positive" in sentiments
    if has_neg and has_pos:
        return SentimentSummary.mixed
    if has_neg:
        return SentimentSummary.negative
    if has_pos:
        return SentimentSummary.positive
    return SentimentSummary.neutral
