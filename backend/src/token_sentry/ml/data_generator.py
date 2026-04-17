"""Synthetic training data generator for token safety scoring."""

import numpy as np
import pandas as pd


def generate_training_data(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic training data based on token risk patterns.

    Produces samples across three risk profiles:
    - Safe (A/B): ~40% of samples
    - Suspicious (C): ~30% of samples
    - Dangerous (D/F): ~30% of samples
    """
    rng = np.random.default_rng(seed)

    n_safe = int(n_samples * 0.4)
    n_suspicious = int(n_samples * 0.3)
    n_dangerous = n_samples - n_safe - n_suspicious

    rows: list[dict] = []

    # Safe tokens (A/B grade, score 60-100)
    for _ in range(n_safe):
        has_hidden_mint = 0
        has_blacklist = int(rng.random() < 0.05)
        has_fee_on_transfer = int(rng.random() < 0.1)
        is_proxy = int(rng.random() < 0.1)
        has_owner_pause = int(rng.random() < 0.1)
        has_owner_mint = int(rng.random() < 0.05)
        critical_flag_count = sum([
            has_hidden_mint, has_blacklist, is_proxy,
            has_owner_pause, has_owner_mint,
        ])
        top10_concentration = rng.uniform(0.1, 0.4)
        whale_percentage = rng.uniform(0.01, 0.15)
        creator_holding = rng.uniform(0.0, 0.1)
        liquidity_depth = rng.uniform(50_000, 500_000)
        liquidity_mcap_ratio = rng.uniform(0.05, 0.3)
        lp_locked = 1
        is_honeypot = 0
        buy_tax = rng.uniform(0.0, 0.03)
        sell_tax = rng.uniform(0.0, 0.05)

        # Score: high, penalize lightly for any flags
        score = 100 - critical_flag_count * 15 - top10_concentration * 10
        score = score - sell_tax * 20 + rng.normal(0, 3)
        score = float(np.clip(score, 60, 100))

        rows.append({
            "has_hidden_mint": has_hidden_mint,
            "has_blacklist": has_blacklist,
            "has_fee_on_transfer": has_fee_on_transfer,
            "is_proxy": is_proxy,
            "has_owner_pause": has_owner_pause,
            "has_owner_mint": has_owner_mint,
            "critical_flag_count": critical_flag_count,
            "top10_concentration": top10_concentration,
            "whale_percentage": whale_percentage,
            "creator_holding": creator_holding,
            "liquidity_depth": liquidity_depth,
            "liquidity_mcap_ratio": liquidity_mcap_ratio,
            "lp_locked": lp_locked,
            "is_honeypot": is_honeypot,
            "buy_tax": buy_tax,
            "sell_tax": sell_tax,
            "safety_score": round(score, 1),
        })

    # Suspicious tokens (C grade, score 40-59)
    for _ in range(n_suspicious):
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
        top10_concentration = rng.uniform(0.3, 0.7)
        whale_percentage = rng.uniform(0.1, 0.4)
        creator_holding = rng.uniform(0.05, 0.3)
        liquidity_depth = rng.uniform(5_000, 80_000)
        liquidity_mcap_ratio = rng.uniform(0.01, 0.1)
        lp_locked = int(rng.random() < 0.5)
        is_honeypot = 0
        buy_tax = rng.uniform(0.01, 0.1)
        sell_tax = rng.uniform(0.03, 0.15)

        score = 70 - critical_flag_count * 10 - top10_concentration * 15
        score = score - sell_tax * 30 - (1 - lp_locked) * 8 + rng.normal(0, 4)
        score = float(np.clip(score, 40, 59))

        rows.append({
            "has_hidden_mint": has_hidden_mint,
            "has_blacklist": has_blacklist,
            "has_fee_on_transfer": has_fee_on_transfer,
            "is_proxy": is_proxy,
            "has_owner_pause": has_owner_pause,
            "has_owner_mint": has_owner_mint,
            "critical_flag_count": critical_flag_count,
            "top10_concentration": top10_concentration,
            "whale_percentage": whale_percentage,
            "creator_holding": creator_holding,
            "liquidity_depth": liquidity_depth,
            "liquidity_mcap_ratio": liquidity_mcap_ratio,
            "lp_locked": lp_locked,
            "is_honeypot": is_honeypot,
            "buy_tax": buy_tax,
            "sell_tax": sell_tax,
            "safety_score": round(score, 1),
        })

    # Dangerous tokens (D/F grade, score 0-39)
    for _ in range(n_dangerous):
        has_hidden_mint = int(rng.random() < 0.5)
        has_blacklist = int(rng.random() < 0.6)
        has_fee_on_transfer = int(rng.random() < 0.6)
        is_proxy = int(rng.random() < 0.5)
        has_owner_pause = int(rng.random() < 0.5)
        has_owner_mint = int(rng.random() < 0.5)
        critical_flag_count = sum([
            has_hidden_mint, has_blacklist, is_proxy,
            has_owner_pause, has_owner_mint,
        ])
        top10_concentration = rng.uniform(0.5, 1.0)
        whale_percentage = rng.uniform(0.3, 0.9)
        creator_holding = rng.uniform(0.2, 0.8)
        liquidity_depth = rng.uniform(0, 10_000)
        liquidity_mcap_ratio = rng.uniform(0.0, 0.03)
        lp_locked = int(rng.random() < 0.1)
        is_honeypot = int(rng.random() < 0.6)
        buy_tax = rng.uniform(0.05, 0.5)
        sell_tax = rng.uniform(0.1, 1.0)

        score = 50 - critical_flag_count * 10 - is_honeypot * 25
        score = score - top10_concentration * 15 - sell_tax * 20
        score = score - (1 - lp_locked) * 5 + rng.normal(0, 3)
        score = float(np.clip(score, 0, 39))

        rows.append({
            "has_hidden_mint": has_hidden_mint,
            "has_blacklist": has_blacklist,
            "has_fee_on_transfer": has_fee_on_transfer,
            "is_proxy": is_proxy,
            "has_owner_pause": has_owner_pause,
            "has_owner_mint": has_owner_mint,
            "critical_flag_count": critical_flag_count,
            "top10_concentration": top10_concentration,
            "whale_percentage": whale_percentage,
            "creator_holding": creator_holding,
            "liquidity_depth": liquidity_depth,
            "liquidity_mcap_ratio": liquidity_mcap_ratio,
            "lp_locked": lp_locked,
            "is_honeypot": is_honeypot,
            "buy_tax": buy_tax,
            "sell_tax": sell_tax,
            "safety_score": round(score, 1),
        })

    df = pd.DataFrame(rows)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


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
