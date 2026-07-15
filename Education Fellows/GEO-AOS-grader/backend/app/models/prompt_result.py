from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class PromptResult(Base):
    __tablename__ = "prompt_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    citations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    brand_cited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    competitors_cited: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    competitors_mentioned: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sentiment: Mapped[Sentiment | None] = mapped_column(
        Enum(Sentiment, name="prompt_sentiment"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
