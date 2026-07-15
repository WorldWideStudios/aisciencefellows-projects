from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.analyze import Competitor


class SourceShareEntry(BaseModel):
    domain: str
    count: int
    is_brand: bool
    is_competitor: bool


class PromptResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    raw_response: str
    citations: list[str]
    brand_cited: bool
    brand_mentioned: bool
    competitors_cited: list[str]
    competitors_mentioned: list[str]
    sentiment: str | None = None
    error: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    url: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    brand_name: str | None = None
    brand_domain: str | None = None
    brand_aliases: list[str] | None = None
    brand_description: str | None = None
    industry: str | None = None
    competitors: list[Competitor] | None = None
    prompts: list[str] | None = None

    aeo_score: float | None = None
    citation_rate: float | None = None
    mention_rate: float | None = None
    sentiment_summary: str | None = None
    source_share_of_voice: list[SourceShareEntry] | None = None

    prompt_results: list[PromptResultOut] = []
