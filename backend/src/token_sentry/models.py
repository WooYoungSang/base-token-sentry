"""Shared dataclasses for Token Sentry analysis results."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContractAnalysis:
    address: str
    has_hidden_mint: bool = False
    has_blacklist: bool = False
    has_fee_on_transfer: bool = False
    is_proxy: bool = False
    has_owner_pause: bool = False
    has_owner_blacklist: bool = False
    has_owner_mint: bool = False
    risk_flags: list[str] = field(default_factory=list)
    verified_source: bool = False

    @property
    def critical_flag_count(self) -> int:
        return sum([
            self.has_hidden_mint,
            self.has_blacklist,
            self.is_proxy,
            self.has_owner_pause,
            self.has_owner_blacklist,
            self.has_owner_mint,
        ])


@dataclass
class HolderAnalysis:
    address: str
    top10_concentration: float = 0.0  # 0-1
    whale_percentage: float = 0.0     # largest single holder 0-1
    creator_holding: float = 0.0      # 0-1
    single_holder_dominant: bool = False  # >50%
    creator_dominant: bool = False        # >80%
    total_holders: int = 0


@dataclass
class LiquidityAnalysis:
    address: str
    total_liquidity_usd: float = 0.0
    liquidity_mcap_ratio: float = 0.0
    lp_locked: bool = False
    low_liquidity: bool = False
    pool_count: int = 0


@dataclass
class HoneypotResult:
    address: str
    is_honeypot: bool = False
    buy_tax: float = 0.0    # 0-1
    sell_tax: float = 0.0   # 0-1
    buy_blocked: bool = False
    sell_blocked: bool = False
    details: str = ""


@dataclass
class SafetyScore:
    address: str
    score: int = 100  # 0-100
    grade: str = "A"
    penalties: list[str] = field(default_factory=list)
    contract: Optional[ContractAnalysis] = None
    holder: Optional[HolderAnalysis] = None
    liquidity: Optional[LiquidityAnalysis] = None
    honeypot: Optional[HoneypotResult] = None
    scoring_method: str = "rule_based"
    ml_confidence: Optional[float] = None

    def _compute_grade(self) -> str:
        if self.score >= 80:
            return "A"
        elif self.score >= 60:
            return "B"
        elif self.score >= 40:
            return "C"
        elif self.score >= 20:
            return "D"
        return "F"
