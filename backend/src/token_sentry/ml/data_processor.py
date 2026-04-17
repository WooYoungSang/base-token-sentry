"""Convert raw GoPlusLabs + Basescan API data into ML training features."""

import logging
from pathlib import Path

import pandas as pd

from .data_generator import FEATURE_COLUMNS
from .token_lists import get_label_hint

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
TRAINING_DATA_PATH = DATA_DIR / "token_training_data.csv"


def _safe_float(value: str | int | float | None, default: float = 0.0) -> float:
    """Convert a GoPlusLabs string value to float safely."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: str | int | None, default: int = 0) -> int:
    """Convert a GoPlusLabs string value to int safely."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_bool(value: str | int | None) -> int:
    """Convert a GoPlusLabs '0'/'1' string to int (0 or 1)."""
    if value is None or value == "":
        return 0
    try:
        return 1 if int(value) == 1 else 0
    except (ValueError, TypeError):
        return 0


def extract_features_from_goplus(goplus_data: dict) -> dict[str, float]:
    """Extract the 16 ML features from a GoPlusLabs token_security response.

    Maps GoPlusLabs fields to the existing FEATURE_COLUMNS used by the model.
    """
    is_honeypot = _safe_bool(goplus_data.get("is_honeypot"))
    is_proxy = _safe_bool(goplus_data.get("is_proxy"))
    hidden_owner = _safe_bool(goplus_data.get("hidden_owner"))
    is_mintable = _safe_bool(goplus_data.get("is_mintable"))
    transfer_pausable = _safe_bool(goplus_data.get("transfer_pausable"))
    is_blacklisted = _safe_bool(goplus_data.get("is_blacklisted"))
    is_whitelisted = _safe_bool(goplus_data.get("is_whitelisted"))

    buy_tax = _safe_float(goplus_data.get("buy_tax"))
    sell_tax = _safe_float(goplus_data.get("sell_tax"))

    # Map has_fee_on_transfer from tax presence
    has_fee_on_transfer = 1 if (buy_tax > 0.001 or sell_tax > 0.001) else 0

    # has_hidden_mint: mintable + hidden owner is the worst combo
    has_hidden_mint = 1 if (is_mintable and hidden_owner) else 0

    # has_blacklist: direct blacklist or whitelist mechanism
    has_blacklist = 1 if (is_blacklisted or is_whitelisted) else 0

    # has_owner_pause: transfer can be paused
    has_owner_pause = transfer_pausable

    # has_owner_mint: owner can mint
    has_owner_mint = is_mintable

    # critical_flag_count
    critical_flag_count = sum([
        has_hidden_mint, has_blacklist, is_proxy,
        has_owner_pause, has_owner_mint,
    ])

    # Holder data from GoPlusLabs (if available)
    holders = goplus_data.get("holders", [])

    top10_concentration = 0.0
    whale_percentage = 0.0
    creator_holding = 0.0

    if holders and isinstance(holders, list):
        # Top 10 concentration
        top10 = holders[:10]
        top10_concentration = sum(_safe_float(h.get("percent")) for h in top10)
        # Whale = largest single holder
        if top10:
            whale_percentage = _safe_float(top10[0].get("percent"))
        # Creator holding = check if creator tag exists
        creator_address = goplus_data.get("creator_address", "").lower()
        for h in holders:
            if h.get("address", "").lower() == creator_address:
                creator_holding = _safe_float(h.get("percent"))
                break

    # Liquidity data from GoPlusLabs
    lp_total_supply = _safe_float(goplus_data.get("lp_total_supply"))

    # Estimate liquidity depth from LP data (GoPlusLabs doesn't give USD directly)
    # Use lp_total_supply as a rough proxy; real depth requires DEX query
    liquidity_depth = lp_total_supply if lp_total_supply > 0 else 0.0

    # LP locked detection from lp_holders
    lp_holders = goplus_data.get("lp_holders", [])
    lp_locked = 0
    if lp_holders and isinstance(lp_holders, list):
        for lp_h in lp_holders:
            if _safe_bool(lp_h.get("is_locked")):
                lp_locked = 1
                break

    # liquidity_mcap_ratio: approximate from available data
    total_supply = _safe_float(goplus_data.get("total_supply"))
    liquidity_mcap_ratio = 0.0
    if total_supply > 0 and liquidity_depth > 0:
        liquidity_mcap_ratio = min(liquidity_depth / total_supply, 1.0)

    return {
        "has_hidden_mint": float(has_hidden_mint),
        "has_blacklist": float(has_blacklist),
        "has_fee_on_transfer": float(has_fee_on_transfer),
        "is_proxy": float(is_proxy),
        "has_owner_pause": float(has_owner_pause),
        "has_owner_mint": float(has_owner_mint),
        "critical_flag_count": float(critical_flag_count),
        "top10_concentration": top10_concentration,
        "whale_percentage": whale_percentage,
        "creator_holding": creator_holding,
        "liquidity_depth": liquidity_depth,
        "liquidity_mcap_ratio": liquidity_mcap_ratio,
        "lp_locked": float(lp_locked),
        "is_honeypot": float(is_honeypot),
        "buy_tax": buy_tax,
        "sell_tax": sell_tax,
    }


def compute_safety_score(goplus_data: dict, label_hint: str | None = None) -> float:
    """Compute a safety score (0-100) from GoPlusLabs risk signals.

    Uses the labeling strategy:
    - is_honeypot=true -> dangerous (0-20)
    - high sell_tax (>10%) -> suspicious (20-50)
    - is_proxy + hidden_owner -> suspicious (30-50)
    - clean flags + listed on major DEX -> safe (70-100)

    label_hint overrides for known tokens: "safe" -> 80-95, "scam" -> 0-20.
    """
    if label_hint == "scam":
        return 10.0
    if label_hint == "safe":
        return 85.0

    score = 100.0

    is_honeypot = _safe_bool(goplus_data.get("is_honeypot"))
    sell_tax = _safe_float(goplus_data.get("sell_tax"))
    buy_tax = _safe_float(goplus_data.get("buy_tax"))
    is_proxy = _safe_bool(goplus_data.get("is_proxy"))
    hidden_owner = _safe_bool(goplus_data.get("hidden_owner"))
    is_mintable = _safe_bool(goplus_data.get("is_mintable"))
    transfer_pausable = _safe_bool(goplus_data.get("transfer_pausable"))
    is_blacklisted = _safe_bool(goplus_data.get("is_blacklisted"))
    cannot_sell_all = _safe_bool(goplus_data.get("cannot_sell_all"))
    selfdestruct = _safe_bool(goplus_data.get("selfdestruct"))
    owner_change_balance = _safe_bool(goplus_data.get("owner_change_balance"))
    is_open_source = _safe_bool(goplus_data.get("is_open_source"))

    # Critical flags
    if is_honeypot:
        score -= 70
    if cannot_sell_all:
        score -= 60
    if selfdestruct:
        score -= 40
    if owner_change_balance:
        score -= 30

    # Tax penalties
    if sell_tax > 0.5:
        score -= 40
    elif sell_tax > 0.1:
        score -= 25
    elif sell_tax > 0.05:
        score -= 10

    if buy_tax > 0.5:
        score -= 30
    elif buy_tax > 0.1:
        score -= 15
    elif buy_tax > 0.05:
        score -= 5

    # Ownership risks
    if hidden_owner:
        score -= 20
    if is_proxy:
        score -= 10
    if is_mintable:
        score -= 10
    if transfer_pausable:
        score -= 10
    if is_blacklisted:
        score -= 10

    # Bonus for verified source
    if is_open_source:
        score += 5

    return max(0.0, min(100.0, score))


def process_records(records: list[dict]) -> pd.DataFrame:
    """Convert raw collected records into a training DataFrame.

    Each record has: {address, goplus_data, basescan_source}.
    Returns DataFrame with FEATURE_COLUMNS + safety_score + address.
    """
    rows: list[dict] = []

    for record in records:
        address = record["address"]
        goplus_data = record["goplus_data"]

        features = extract_features_from_goplus(goplus_data)
        label_hint = get_label_hint(address)
        safety_score = compute_safety_score(goplus_data, label_hint=label_hint)

        row = {"address": address, **features, "safety_score": round(safety_score, 1)}
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Ensure column order matches expected format
    output_cols = ["address"] + FEATURE_COLUMNS + ["safety_score"]
    for col in output_cols:
        if col not in df.columns:
            df[col] = 0.0
    return df[output_cols]


def save_training_data(df: pd.DataFrame, path: Path | None = None) -> Path:
    """Save processed training data to CSV."""
    if path is None:
        path = TRAINING_DATA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Saved %d training samples to %s", len(df), path)
    return path


def load_training_data(path: Path | None = None) -> pd.DataFrame | None:
    """Load training data from CSV if it exists."""
    if path is None:
        path = TRAINING_DATA_PATH
    if not path.exists():
        return None
    return pd.read_csv(path)
