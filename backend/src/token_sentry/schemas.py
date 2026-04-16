"""Pydantic v2 response schemas for Token Sentry API."""

from typing import Optional

from pydantic import BaseModel, Field

DISCLAIMER = "Safety scores are informational only, not investment advice."


class ContractAnalysisSchema(BaseModel):
    has_hidden_mint: bool
    has_blacklist: bool
    has_fee_on_transfer: bool
    is_proxy: bool
    has_owner_pause: bool
    has_owner_blacklist: bool
    has_owner_mint: bool
    risk_flags: list[str]
    verified_source: bool
    critical_flag_count: int


class HolderAnalysisSchema(BaseModel):
    top10_concentration: float
    whale_percentage: float
    creator_holding: float
    single_holder_dominant: bool
    creator_dominant: bool
    total_holders: int


class LiquidityAnalysisSchema(BaseModel):
    total_liquidity_usd: float
    liquidity_mcap_ratio: float
    lp_locked: bool
    low_liquidity: bool
    pool_count: int


class HoneypotResultSchema(BaseModel):
    is_honeypot: bool
    buy_tax: float
    sell_tax: float
    buy_blocked: bool
    sell_blocked: bool
    details: str


class SafetyScoreSchema(BaseModel):
    address: str
    score: int = Field(ge=0, le=100)
    grade: str
    penalties: list[str]
    disclaimer: str = DISCLAIMER


class TokenDetailSchema(BaseModel):
    address: str
    score: int = Field(ge=0, le=100)
    grade: str
    penalties: list[str]
    contract: Optional[ContractAnalysisSchema] = None
    holder: Optional[HolderAnalysisSchema] = None
    liquidity: Optional[LiquidityAnalysisSchema] = None
    honeypot: Optional[HoneypotResultSchema] = None
    analyzed_at: Optional[str] = None
    disclaimer: str = DISCLAIMER


class TokenListItem(BaseModel):
    address: str
    score: int
    grade: str
    is_honeypot: bool
    analyzed_at: Optional[str] = None


class TokenListResponse(BaseModel):
    tokens: list[TokenListItem]
    total: int
    page: int
    page_size: int
    disclaimer: str = DISCLAIMER


class AnalyzeResponse(BaseModel):
    address: str
    score: int
    grade: str
    is_honeypot: bool
    disclaimer: str = DISCLAIMER


class RecentTokenSchema(BaseModel):
    address: str
    detected_at: str


class RecentTokensResponse(BaseModel):
    tokens: list[RecentTokenSchema]
    count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
