"""Оркестрация анализа сайта: парсинг → brand_analyzer → prompt_generator."""
from __future__ import annotations

import uuid

from loguru import logger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Report, ReportStatus
from app.services.brand_analyzer import BrandAnalyzerError, analyze_brand
from app.services.prompt_generator import PromptGeneratorError, generate_prompts
from app.services.site_parser import SiteParseError, parse_site


async def _fail(report_id: uuid.UUID, error: str) -> None:
    async with AsyncSessionLocal() as session:
        report = await session.get(Report, report_id)
        if report is None:
            return
        report.status = ReportStatus.failed
        report.error = error
        await session.commit()


async def analyze_site_task(report_id: uuid.UUID) -> None:
    logger.info("analyze_site: start report_id={}", report_id)

    async with AsyncSessionLocal() as session:
        report = await session.get(Report, report_id)
        if report is None:
            logger.error("analyze_site: report {} not found", report_id)
            return
        url = report.url

    try:
        site_data = await parse_site(url)
    except SiteParseError as e:
        logger.warning("analyze_site: site_parser failed for {}: {}", url, e)
        await _fail(report_id, str(e))
        return
    except Exception as e:
        logger.exception("analyze_site: unexpected site_parser error: {}", e)
        await _fail(report_id, "Не удалось обработать сайт")
        return

    try:
        brand = await analyze_brand(site_data)
    except BrandAnalyzerError as e:
        logger.warning("analyze_site: brand_analyzer failed: {}", e)
        await _fail(report_id, "Не удалось проанализировать бренд")
        return
    except Exception as e:
        logger.exception("analyze_site: unexpected brand_analyzer error: {}", e)
        await _fail(report_id, "Ошибка анализа бренда")
        return

    try:
        prompts = await generate_prompts(brand)
    except PromptGeneratorError as e:
        logger.warning("analyze_site: prompt_generator failed: {}", e)
        await _fail(report_id, "Не удалось сгенерировать поисковые запросы")
        return
    except Exception as e:
        logger.exception("analyze_site: unexpected prompt_generator error: {}", e)
        await _fail(report_id, "Ошибка генерации запросов")
        return

    async with AsyncSessionLocal() as session:
        report = await session.get(Report, report_id)
        if report is None:
            return
        report.brand_name = brand["brand_name"]
        report.brand_domain = brand["brand_domain"]
        report.brand_aliases = brand["brand_aliases"]
        report.brand_description = brand.get("brand_description")
        report.industry = brand.get("industry")
        report.competitors = brand["competitors"]
        report.prompts = prompts
        report.status = ReportStatus.awaiting_confirmation
        await session.commit()

    logger.info("analyze_site: done report_id={} brand={}", report_id, brand["brand_name"])
