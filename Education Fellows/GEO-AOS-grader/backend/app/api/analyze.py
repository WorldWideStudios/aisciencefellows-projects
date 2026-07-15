"""Эндпоинты первого этапа: создание анализа, статус, подтверждение."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Report, ReportStatus
from app.schemas.analyze import (
    AnalyzeCreatedResponse,
    AnalyzePatchRequest,
    AnalyzeRequest,
    AnalyzeStatusResponse,
)
from app.services.url_validator import InvalidURLError, validate_public_url
from app.tasks.analyze_site import analyze_site_task
from app.tasks.generate_report import generate_report_task

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AnalyzeCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    payload: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> AnalyzeCreatedResponse:
    try:
        url = validate_public_url(str(payload.url))
    except InvalidURLError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    report = Report(url=url, status=ReportStatus.analyzing)
    session.add(report)
    await session.commit()
    await session.refresh(report)

    background_tasks.add_task(analyze_site_task, report.id)

    return AnalyzeCreatedResponse(id=report.id, status=report.status.value)


@router.get("/{report_id}", response_model=AnalyzeStatusResponse)
async def get_analysis(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> AnalyzeStatusResponse:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return AnalyzeStatusResponse(
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
    )


@router.patch("/{report_id}", response_model=AnalyzeCreatedResponse)
async def update_analysis(
    report_id: uuid.UUID,
    payload: AnalyzePatchRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> AnalyzeCreatedResponse:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if report.status != ReportStatus.awaiting_confirmation:
        raise HTTPException(
            status_code=409,
            detail=f"Отчёт в статусе {report.status.value}, подтверждение недоступно",
        )

    report.brand_name = payload.brand_name
    report.brand_domain = payload.brand_domain.lower().lstrip("www.")
    report.brand_aliases = payload.brand_aliases
    report.competitors = [c.model_dump() for c in payload.competitors]
    report.prompts = payload.prompts
    report.email = payload.email
    report.status = ReportStatus.generating

    await session.commit()
    await session.refresh(report)

    background_tasks.add_task(generate_report_task, report.id)

    return AnalyzeCreatedResponse(id=report.id, status=report.status.value)
