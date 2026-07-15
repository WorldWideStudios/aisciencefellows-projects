from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReportStatus(str, enum.Enum):
    analyzing = "analyzing"
    awaiting_confirmation = "awaiting_confirmation"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class SentimentSummary(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    mixed = "mixed"
    negative = "negative"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        default=ReportStatus.analyzing,
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_aliases: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    brand_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)

    competitors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    prompts: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    aeo_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    mention_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_summary: Mapped[SentimentSummary | None] = mapped_column(
        Enum(SentimentSummary, name="sentiment_summary"), nullable=True
    )
    source_share_of_voice: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
