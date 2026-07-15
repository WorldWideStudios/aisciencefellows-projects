"""Эндпоинт получения сгенерированного отчёта."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import PromptResult, Report
from app.schemas.report import PromptResultOut, ReportOut

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ReportOut:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    result = await session.execute(
        select(PromptResult)
        .where(PromptResult.report_id == report_id)
        .order_by(PromptResult.created_at.asc())
    )
    prompt_results = result.scalars().all()

    return ReportOut(
        id=report.id,
        status=report.status.value,
        url=report.url,
        created_at=report.created_at,
        updated_at=report.updated_at,
        error=report.error,
        brand_name=report.brand_name,
        brand_domain=report.brand_domain,
        brand_aliases=report.brand_aliases,
        brand_description=report.brand_description,
        industry=report.industry,
        competitors=report.competitors,
        prompts=report.prompts,
        aeo_score=report.aeo_score,
        citation_rate=report.citation_rate,
        mention_rate=report.mention_rate,
        sentiment_summary=report.sentiment_summary.value if report.sentiment_summary else None,
        source_share_of_voice=report.source_share_of_voice,
        prompt_results=[PromptResultOut.model_validate(pr) for pr in prompt_results],
    )
