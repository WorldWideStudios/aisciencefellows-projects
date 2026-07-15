"""Оркестрация генерации отчёта: 10 промптов параллельно через Perplexity → метрики."""
from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import PromptResult, Report, ReportStatus, Sentiment
from app.services.citation_matcher import match_citations
from app.services.llm_client import LLMClientError, query
from app.services.mention_matcher import match_mentions
from app.services.score_calculator import calculate_aeo_score, determine_sentiment_summary
from app.services.sentiment_classifier import classify_sentiment
from app.services.source_aggregator import aggregate_sources

FAILURE_THRESHOLD = 0.5  # если упало >50% промптов → отчёт failed


async def _run_one_prompt(
    prompt: str,
    brand_name: str,
    brand_domain: str,
    brand_aliases: list[str],
    competitor_domains: list[str],
    competitor_names: list[str],
) -> dict:
    """Один промпт через Perplexity → распарсенный результат."""
    try:
        response = await query(prompt=prompt, model=settings.MODEL_MAIN)
    except (LLMClientError, asyncio.TimeoutError) as e:
        logger.warning("generate_report: prompt failed {!r}: {}", prompt[:60], e)
        return {"prompt": prompt, "error": str(e)}
    except Exception as e:
        logger.exception("generate_report: unexpected error for prompt {!r}", prompt[:60])
        return {"prompt": prompt, "error": str(e)}

    text = response.text or ""
    citation_data = match_citations(response.citations, brand_domain, competitor_domains)
    mention_data = match_mentions(text, brand_aliases, competitor_names)

    sentiment: Sentiment | None = None
    if mention_data["brand_mentioned"]:
        sentiment = await classify_sentiment(text, brand_name)

    return {
        "prompt": prompt,
        "raw_response": text,
        "citations": citation_data["all_cited_domains"],
        "brand_cited": citation_data["brand_cited"],
        "brand_mentioned": mention_data["brand_mentioned"],
        "competitors_cited": citation_data["competitors_cited"],
        "competitors_mentioned": mention_data["competitors_mentioned"],
        "sentiment": sentiment.value if sentiment else None,
        "error": None,
    }


async def _fail(report_id: uuid.UUID, error: str) -> None:
    async with AsyncSessionLocal() as session:
        report = await session.get(Report, report_id)
        if report is None:
            return
        report.status = ReportStatus.failed
        report.error = error
        await session.commit()


async def generate_report_task(report_id: uuid.UUID) -> None:
    logger.info("generate_report: start report_id={}", report_id)

    async with AsyncSessionLocal() as session:
        report = await session.get(Report, report_id)
        if report is None:
            logger.error("generate_report: report {} not found", report_id)
            return
        brand_name = report.brand_name or ""
        brand_domain = report.brand_domain or ""
        brand_aliases = list(report.brand_aliases or [])
        if brand_name and brand_name not in brand_aliases:
            brand_aliases.append(brand_name)
        competitors = list(report.competitors or [])
        prompts = list(report.prompts or [])

    competitor_domains = [c.get("domain", "") for c in competitors if c.get("domain")]
    competitor_names = [c.get("name", "") for c in competitors if c.get("name")]

    if not prompts:
        await _fail(report_id, "Нет промптов для прогона")
        return

    results = await asyncio.gather(
        *(
            _run_one_prompt(
                p, brand_name, brand_domain, brand_aliases, competitor_domains, competitor_names
            )
            for p in prompts
        ),
        return_exceptions=False,
    )

    failed_count = sum(1 for r in results if r.get("error"))
    total = len(results)
    if total == 0 or failed_count / total > FAILURE_THRESHOLD:
        await _fail(
            report_id,
            f"Не удалось прогнать большинство запросов: {failed_count} из {total} с ошибкой",
        )
        return

    successful = [r for r in results if not r.get("error")]
    n = len(successful)
    citation_rate = sum(1 for r in successful if r["brand_cited"]) / n
    mention_rate = sum(1 for r in successful if r["brand_mentioned"]) / n
    sentiments = [r["sentiment"] for r in successful if r["sentiment"]]
    sentiment_summary = determine_sentiment_summary(sentiments)
    aeo_score = calculate_aeo_score(citation_rate, mention_rate, sentiment_summary.value)

    sov = aggregate_sources(
        [r["citations"] for r in successful],
        brand_domain,
        competitor_domains,
    )

    async with AsyncSessionLocal() as session:
        for r in results:
            pr = PromptResult(
                report_id=report_id,
                prompt=r["prompt"],
                raw_response=r.get("raw_response", "") or "",
                citations=r.get("citations") or [],
                brand_cited=bool(r.get("brand_cited")),
                brand_mentioned=bool(r.get("brand_mentioned")),
                competitors_cited=r.get("competitors_cited") or [],
                competitors_mentioned=r.get("competitors_mentioned") or [],
                sentiment=Sentiment(r["sentiment"]) if r.get("sentiment") else None,
                error=r.get("error"),
            )
            session.add(pr)

        report = await session.get(Report, report_id)
        if report is None:
            return
        report.aeo_score = aeo_score
        report.citation_rate = round(citation_rate, 4)
        report.mention_rate = round(mention_rate, 4)
        report.sentiment_summary = sentiment_summary
        report.source_share_of_voice = sov
        report.status = ReportStatus.completed
        await session.commit()

    logger.info(
        "generate_report: done report_id={} score={} citation_rate={} mention_rate={}",
        report_id, aeo_score, round(citation_rate, 2), round(mention_rate, 2),
    )
