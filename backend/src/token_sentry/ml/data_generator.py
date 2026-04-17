"""Synthetic training data generator for token safety scoring."""

import numpy as np
import pandas as pd


def _make_row(features: dict, score: float) -> dict:
    """Combine feature dict with a safety_score label."""
    features["safety_score"] = round(score, 1)
    return features


def generate_training_data(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic training data based on token risk patterns.

    Uses class-conditional label sampling (not derived from features) to avoid
    data leakage. Produces samples across five grade buckets:
    - Safe A: ~30% of samples
    - Safe B: ~10% of samples (boundary)
    - Suspicious C: ~30% of samples
    - Dangerous D: ~10% of samples (boundary)
    - Dangerous F: ~20% of samples
    """
    rng = np.random.default_rng(seed)

    # Reserve space for edge cases (20 fixed samples)
    n_edge = 20
    n_main = n_samples - n_edge
    n_grade_a = int(n_main * 0.30)
    n_grade_b = int(n_main * 0.10)
    n_grade_c = int(n_main * 0.30)
    n_grade_d = int(n_main * 0.10)
    n_grade_f = n_main - n_grade_a - n_grade_b - n_grade_c - n_grade_d

    rows: list[dict] = []

    # --- Grade A tokens (score 80-100) ---
    for _ in range(n_grade_a):
        features = _gen_safe_features(rng)
        score = float(np.clip(rng.normal(88, 6), 80, 100))
        rows.append(_make_row(features, score))

    # --- Grade B tokens (score 60-79) — boundary representation ---
    for _ in range(n_grade_b):
        features = _gen_safe_features(rng, slightly_risky=True)
        score = float(np.clip(rng.normal(68, 5), 60, 79))
        rows.append(_make_row(features, score))

    # --- Grade C tokens (score 40-59) ---
    for _ in range(n_grade_c):
        features = _gen_suspicious_features(rng)
        score = float(np.clip(rng.normal(48, 6), 30, 59))
        rows.append(_make_row(features, score))

    # --- Grade D tokens (score 20-39) — boundary representation ---
    for _ in range(n_grade_d):
        features = _gen_dangerous_features(rng)
        score = float(np.clip(rng.normal(30, 5), 20, 39))
        rows.append(_make_row(features, score))

    # --- Grade F tokens (score 0-19) ---
    for _ in range(n_grade_f):
        features = _gen_dangerous_features(rng, extreme=True)
        score = float(np.clip(rng.normal(18, 10), 0, 39))
        rows.append(_make_row(features, score))

    # --- Edge cases ---
    rows.extend(_generate_edge_cases(rng))

    df = pd.DataFrame(rows)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def _gen_safe_features(rng: np.random.Generator, slightly_risky: bool = False) -> dict:
    """Generate features for a safe token (A or B grade)."""
    has_hidden_mint = 0
    has_blacklist = int(rng.random() < (0.15 if slightly_risky else 0.05))
    has_fee_on_transfer = int(rng.random() < (0.2 if slightly_risky else 0.1))
    is_proxy = int(rng.random() < (0.2 if slightly_risky else 0.1))
    has_owner_pause = int(rng.random() < (0.2 if slightly_risky else 0.1))
    has_owner_mint = int(rng.random() < (0.1 if slightly_risky else 0.05))
    critical_flag_count = sum([
        has_hidden_mint, has_blacklist, is_proxy,
        has_owner_pause, has_owner_mint,
    ])
    return {
        "has_hidden_mint": has_hidden_mint,
        "has_blacklist": has_blacklist,
        "has_fee_on_transfer": has_fee_on_transfer,
        "is_proxy": is_proxy,
        "has_owner_pause": has_owner_pause,
        "has_owner_mint": has_owner_mint,
        "critical_flag_count": critical_flag_count,
        "top10_concentration": rng.uniform(0.1, 0.5 if slightly_risky else 0.4),
        "whale_percentage": rng.uniform(0.01, 0.2 if slightly_risky else 0.15),
        "creator_holding": rng.uniform(0.0, 0.15 if slightly_risky else 0.1),
        "liquidity_depth": rng.uniform(30_000 if slightly_risky else 50_000, 500_000),
        "liquidity_mcap_ratio": rng.uniform(0.02 if slightly_risky else 0.05, 0.3),
        "lp_locked": 1,
        "is_honeypot": 0,
        "buy_tax": rng.uniform(0.0, 0.05 if slightly_risky else 0.03),
        "sell_tax": rng.uniform(0.0, 0.08 if slightly_risky else 0.05),
    }


def _gen_suspicious_features(rng: np.random.Generator) -> dict:
    """Generate features for a suspicious token (C grade)."""
    has_hidden_mint = int(rng.random() < 0.1)
    has_blacklist = int(rng.random() < 0.3)
    has_fee_on_transfer = int(rng.random() < 0.4)
    is_proxy = int(rng.random() < 0.4)
    has_owner_pause = int(rng.random() < 0.4)
    has_owner_mint = int(rng.random() < 0.2)
    critical_flag_count = sum([
        has_hidden_mint, has_blacklist, is_proxy,
        has_owner_pause, has_owner_mint,
    ])
    return {
        "has_hidden_mint": has_hidden_mint,
        "has_blacklist": has_blacklist,
        "has_fee_on_transfer": has_fee_on_transfer,
        "is_proxy": is_proxy,
        "has_owner_pause": has_owner_pause,
        "has_owner_mint": has_owner_mint,
        "critical_flag_count": critical_flag_count,
        "top10_concentration": rng.uniform(0.3, 0.7),
        "whale_percentage": rng.uniform(0.1, 0.4),
        "creator_holding": rng.uniform(0.05, 0.3),
        "liquidity_depth": rng.uniform(5_000, 80_000),
        "liquidity_mcap_ratio": rng.uniform(0.01, 0.1),
        "lp_locked": int(rng.random() < 0.5),
        "is_honeypot": 0,
        "buy_tax": rng.uniform(0.01, 0.1),
        "sell_tax": rng.uniform(0.03, 0.15),
    }


def _gen_dangerous_features(rng: np.random.Generator, extreme: bool = False) -> dict:
    """Generate features for a dangerous token (D or F grade)."""
    has_hidden_mint = int(rng.random() < (0.7 if extreme else 0.5))
    has_blacklist = int(rng.random() < (0.8 if extreme else 0.6))
    has_fee_on_transfer = int(rng.random() < (0.8 if extreme else 0.6))
    is_proxy = int(rng.random() < (0.6 if extreme else 0.5))
    has_owner_pause = int(rng.random() < (0.7 if extreme else 0.5))
    has_owner_mint = int(rng.random() < (0.7 if extreme else 0.5))
    critical_flag_count = sum([
        has_hidden_mint, has_blacklist, is_proxy,
        has_owner_pause, has_owner_mint,
    ])
    return {
        "has_hidden_mint": has_hidden_mint,
        "has_blacklist": has_blacklist,
        "has_fee_on_transfer": has_fee_on_transfer,
        "is_proxy": is_proxy,
        "has_owner_pause": has_owner_pause,
        "has_owner_mint": has_owner_mint,
        "critical_flag_count": critical_flag_count,
        "top10_concentration": rng.uniform(0.5, 1.0),
        "whale_percentage": rng.uniform(0.3, 0.9),
        "creator_holding": rng.uniform(0.2, 0.8),
        "liquidity_depth": rng.uniform(0, 10_000),
        "liquidity_mcap_ratio": rng.uniform(0.0, 0.03),
        "lp_locked": int(rng.random() < 0.1),
        "is_honeypot": int(rng.random() < (0.8 if extreme else 0.6)),
        "buy_tax": rng.uniform(0.05, 0.5),
        "sell_tax": rng.uniform(0.1, 1.0),
    }


def _generate_edge_cases(rng: np.random.Generator) -> list[dict]:
    """Generate explicit edge-case samples for model robustness."""
    cases: list[dict] = []

    # Edge case 1: Zero liquidity token — should be dangerous
    for _ in range(5):
        features = _gen_dangerous_features(rng)
        features["liquidity_depth"] = 0.0
        features["liquidity_mcap_ratio"] = 0.0
        features["lp_locked"] = 0
        score = float(np.clip(rng.normal(10, 5), 0, 25))
        cases.append(_make_row(features, score))

    # Edge case 2: 100% sell tax — definite honeypot/scam
    for _ in range(5):
        features = _gen_dangerous_features(rng, extreme=True)
        features["sell_tax"] = 1.0
        features["is_honeypot"] = 1
        score = float(np.clip(rng.normal(5, 3), 0, 15))
        cases.append(_make_row(features, score))

    # Edge case 3: Single holder owns everything
    for _ in range(5):
        features = _gen_dangerous_features(rng)
        features["top10_concentration"] = 1.0
        features["whale_percentage"] = 0.95
        features["creator_holding"] = 0.9
        score = float(np.clip(rng.normal(12, 5), 0, 30))
        cases.append(_make_row(features, score))

    # Edge case 4: Clean token — no flags, good liquidity
    for _ in range(5):
        cases.append(_make_row({
            "has_hidden_mint": 0,
            "has_blacklist": 0,
            "has_fee_on_transfer": 0,
            "is_proxy": 0,
            "has_owner_pause": 0,
            "has_owner_mint": 0,
            "critical_flag_count": 0,
            "top10_concentration": rng.uniform(0.1, 0.25),
            "whale_percentage": rng.uniform(0.01, 0.05),
            "creator_holding": rng.uniform(0.0, 0.03),
            "liquidity_depth": rng.uniform(200_000, 1_000_000),
            "liquidity_mcap_ratio": rng.uniform(0.1, 0.4),
            "lp_locked": 1,
            "is_honeypot": 0,
            "buy_tax": 0.0,
            "sell_tax": 0.0,
        }, float(np.clip(rng.normal(92, 4), 85, 100))))

    return cases


FEATURE_COLUMNS = [
    "has_hidden_mint",
    "has_blacklist",
    "has_fee_on_transfer",
    "is_proxy",
    "has_owner_pause",
    "has_owner_mint",
    "critical_flag_count",
    "top10_concentration",
    "whale_percentage",
    "creator_holding",
    "liquidity_depth",
    "liquidity_mcap_ratio",
    "lp_locked",
    "is_honeypot",
    "buy_tax",
    "sell_tax",
]
