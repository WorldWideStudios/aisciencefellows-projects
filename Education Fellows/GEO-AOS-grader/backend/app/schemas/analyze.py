from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class Competitor(BaseModel):
    name: str
    domain: str


class AnalyzeRequest(BaseModel):
    url: HttpUrl


class AnalyzeCreatedResponse(BaseModel):
    id: uuid.UUID
    status: str


class AnalyzeStatusResponse(BaseModel):
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


class AnalyzePatchRequest(BaseModel):
    brand_name: str = Field(min_length=1, max_length=255)
    brand_domain: str = Field(min_length=1, max_length=255)
    brand_aliases: list[str] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    prompts: list[str] = Field(min_length=1, max_length=20)
    email: EmailStr | None = None
