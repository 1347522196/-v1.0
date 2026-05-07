from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ProductStatus = Literal["new", "tracking", "follow_up", "archived"]
KeywordStatus = Literal["active", "paused", "archived"]
CompetitorStatus = Literal["watching", "testing", "won", "lost", "archived"]


class ScrapeRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)
    marketplace: str = Field(default="com", min_length=2, max_length=10)
    max_pages: int | None = Field(default=None, ge=1, le=20)
    department: str = Field(default="", min_length=0, max_length=30)
    target_products: int = Field(default=100, ge=10, le=200)
    delay_seconds: float = Field(default=1.0, ge=0.0, le=10.0)


class ProductUpdate(BaseModel):
    custom_status: ProductStatus | None = None
    note: str | None = Field(default=None, max_length=1000)
    is_favorite: bool | None = None


class KeywordCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)
    marketplace: str = Field(default="com", min_length=2, max_length=10)
    department: str = Field(default="", min_length=0, max_length=30)
    priority: int = Field(default=3, ge=1, le=5)
    note: str = Field(default="", max_length=500)


class KeywordUpdate(BaseModel):
    status: KeywordStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)


class CompetitorCreate(BaseModel):
    asin: str = Field(min_length=3, max_length=20)
    marketplace: str = Field(default="com", min_length=2, max_length=10)
    keyword_hint: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=500)


class CompetitorUpdate(BaseModel):
    watch_status: CompetitorStatus | None = None
    note: str | None = Field(default=None, max_length=500)


class ProductListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class ActionResponse(BaseModel):
    message: str


class AISettingsUpdate(BaseModel):
    api_key: str = Field(default="", max_length=300)
    model: str = Field(default="deepseek-v4-flash", max_length=60)


class AIAnalyzeRequest(BaseModel):
    scope: Literal["products", "favorites", "keywords"] = "favorites"
    question: str = Field(default="", max_length=2000)
