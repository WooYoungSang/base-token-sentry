"""Tests for data collection pipeline: API parsing, feature extraction, labeling."""

import json
from unittest.mock import patch

import pytest
from token_sentry.ml.data_collector import BasescanCollector, GoPlusCollector
from token_sentry.ml.data_generator import FEATURE_COLUMNS
from token_sentry.ml.data_processor import (
    compute_safety_score,
    extract_features_from_goplus,
    process_records,
)
from token_sentry.ml.token_lists import KNOWN_SCAMS, SAFE_TOKENS, get_label_hint

# --- Sample API responses for mocking ---

SAMPLE_GOPLUS_SAFE = {
    "is_honeypot": "0",
    "is_open_source": "1",
    "is_proxy": "0",
    "is_mintable": "0",
    "hidden_owner": "0",
    "selfdestruct": "0",
    "external_call": "0",
    "buy_tax": "0.0",
    "sell_tax": "0.0",
    "owner_change_balance": "0",
    "transfer_pausable": "0",
    "is_blacklisted": "0",
    "is_whitelisted": "0",
    "cannot_sell_all": "0",
    "holder_count": "5000",
    "lp_holder_count": "100",
    "lp_total_supply": "1000000",
    "is_anti_whale": "0",
    "total_supply": "10000000",
    "holders": [
        {"address": "0xaaa", "percent": "0.05"},
        {"address": "0xbbb", "percent": "0.04"},
        {"address": "0xccc", "percent": "0.03"},
    ],
    "lp_holders": [
        {"address": "0xddd", "is_locked": "1", "percent": "0.8"},
    ],
    "creator_address": "0xaaa",
}

SAMPLE_GOPLUS_HONEYPOT = {
    "is_honeypot": "1",
    "is_open_source": "0",
    "is_proxy": "1",
    "is_mintable": "1",
    "hidden_owner": "1",
    "selfdestruct": "1",
    "external_call": "1",
    "buy_tax": "0.05",
    "sell_tax": "0.99",
    "owner_change_balance": "1",
    "transfer_pausable": "1",
    "is_blacklisted": "1",
    "is_whitelisted": "0",
    "cannot_sell_all": "1",
    "holder_count": "10",
    "lp_holder_count": "1",
    "lp_total_supply": "100",
    "is_anti_whale": "0",
    "total_supply": "1000000",
    "holders": [
        {"address": "0xeee", "percent": "0.95"},
    ],
    "lp_holders": [],
    "creator_address": "0xeee",
}

SAMPLE_GOPLUS_MODERATE = {
    "is_honeypot": "0",
    "is_open_source": "1",
    "is_proxy": "1",
    "is_mintable": "1",
    "hidden_owner": "0",
    "selfdestruct": "0",
    "external_call": "0",
    "buy_tax": "0.01",
    "sell_tax": "0.08",
    "owner_change_balance": "0",
    "transfer_pausable": "1",
    "is_blacklisted": "0",
    "is_whitelisted": "0",
    "cannot_sell_all": "0",
    "holder_count": "500",
    "lp_holder_count": "20",
    "lp_total_supply": "50000",
    "is_anti_whale": "1",
    "total_supply": "5000000",
    "holders": [
        {"address": "0xfff", "percent": "0.15"},
        {"address": "0xggg", "percent": "0.10"},
    ],
    "lp_holders": [
        {"address": "0xhhh", "is_locked": "0", "percent": "0.5"},
    ],
    "creator_address": "0xfff",
}

SAMPLE_BASESCAN_SOURCE = {
    "SourceCode": "pragma solidity ^0.8.0; contract Token {}",
    "ABI": "[]",
    "ContractName": "Token",
    "CompilerVersion": "v0.8.20",
    "OptimizationUsed": "1",
    "Runs": "200",
    "ConstructorArguments": "",
    "EVMVersion": "Default",
    "Library": "",
    "LicenseType": "MIT",
    "Proxy": "0",
    "Implementation": "",
    "SwarmSource": "",
}


class TestGoPlusResponseParsing:
    """Test parsing of GoPlusLabs API responses."""

    def test_safe_token_features(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_SAFE)
        assert features["is_honeypot"] == 0.0
        assert features["is_proxy"] == 0.0
        assert features["has_owner_mint"] == 0.0
        assert features["has_hidden_mint"] == 0.0
        assert features["buy_tax"] == 0.0
        assert features["sell_tax"] == 0.0
        assert features["lp_locked"] == 1.0

    def test_honeypot_features(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_HONEYPOT)
        assert features["is_honeypot"] == 1.0
        assert features["is_proxy"] == 1.0
        assert features["has_owner_mint"] == 1.0
        assert features["has_hidden_mint"] == 1.0
        assert features["sell_tax"] == 0.99
        assert features["has_blacklist"] == 1.0
        assert features["has_owner_pause"] == 1.0

    def test_moderate_token_features(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_MODERATE)
        assert features["is_honeypot"] == 0.0
        assert features["is_proxy"] == 1.0
        assert features["has_owner_mint"] == 1.0
        assert features["has_owner_pause"] == 1.0
        assert features["sell_tax"] == 0.08
        assert features["lp_locked"] == 0.0

    def test_all_feature_columns_present(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_SAFE)
        for col in FEATURE_COLUMNS:
            assert col in features, f"Missing feature: {col}"

    def test_feature_values_are_numeric(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_HONEYPOT)
        for col, val in features.items():
            assert isinstance(val, (int, float)), f"{col} is not numeric: {type(val)}"

    def test_empty_goplus_data(self):
        features = extract_features_from_goplus({})
        assert len(features) == len(FEATURE_COLUMNS)
        # All should be 0 or 0.0 for empty data
        for col in FEATURE_COLUMNS:
            assert col in features

    def test_holder_concentration_extraction(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_SAFE)
        assert features["top10_concentration"] == pytest.approx(0.12, abs=0.01)
        assert features["whale_percentage"] == pytest.approx(0.05)
        assert features["creator_holding"] == pytest.approx(0.05)

    def test_critical_flag_count(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_HONEYPOT)
        # has_hidden_mint(1) + has_blacklist(1) + is_proxy(1) + has_owner_pause(1) + has_owner_mint(1)
        assert features["critical_flag_count"] == 5.0

    def test_critical_flag_count_safe(self):
        features = extract_features_from_goplus(SAMPLE_GOPLUS_SAFE)
        assert features["critical_flag_count"] == 0.0


class TestBasescanResponseParsing:
    """Test Basescan API response handling with mocked HTTP."""

    @patch("token_sentry.ml.data_collector.httpx.Client")
    def test_source_code_caching(self, mock_client_cls, tmp_path):
        cache_file = tmp_path / "0xtest_source.json"
        cache_file.write_text(json.dumps(SAMPLE_BASESCAN_SOURCE))

        collector = BasescanCollector(api_key="test_key")
        with patch("token_sentry.ml.data_collector.RAW_BASESCAN_DIR", tmp_path):
            result = collector.get_source_code("0xtest")

        assert result is not None
        assert result["ContractName"] == "Token"
        # Should not have made HTTP request (cache hit)
        mock_client_cls.assert_not_called()

    @patch("token_sentry.ml.data_collector.httpx.Client")
    def test_goplus_caching(self, mock_client_cls, tmp_path):
        cache_file = tmp_path / "0xtest.json"
        cache_file.write_text(json.dumps(SAMPLE_GOPLUS_SAFE))

        collector = GoPlusCollector()
        with patch("token_sentry.ml.data_collector.RAW_GOPLUS_DIR", tmp_path):
            result = collector.fetch_token_security("0xtest")

        assert result is not None
        assert result["is_honeypot"] == "0"
        mock_client_cls.assert_not_called()


class TestDataProcessorFeatureExtraction:
    """Test the full data processor pipeline."""

    def test_process_records_produces_correct_columns(self):
        records = [
            {
                "address": "0xabc123",
                "goplus_data": SAMPLE_GOPLUS_SAFE,
                "basescan_source": SAMPLE_BASESCAN_SOURCE,
            },
        ]
        df = process_records(records)
        assert "address" in df.columns
        assert "safety_score" in df.columns
        for col in FEATURE_COLUMNS:
            assert col in df.columns

    def test_process_multiple_records(self):
        records = [
            {"address": "0xaaa", "goplus_data": SAMPLE_GOPLUS_SAFE, "basescan_source": None},
            {"address": "0xbbb", "goplus_data": SAMPLE_GOPLUS_HONEYPOT, "basescan_source": None},
            {"address": "0xccc", "goplus_data": SAMPLE_GOPLUS_MODERATE, "basescan_source": None},
        ]
        df = process_records(records)
        assert len(df) == 3

    def test_process_empty_records(self):
        df = process_records([])
        assert df.empty

    def test_safety_scores_in_range(self):
        records = [
            {"address": "0xaaa", "goplus_data": SAMPLE_GOPLUS_SAFE, "basescan_source": None},
            {"address": "0xbbb", "goplus_data": SAMPLE_GOPLUS_HONEYPOT, "basescan_source": None},
        ]
        df = process_records(records)
        assert all(0 <= s <= 100 for s in df["safety_score"])


class TestLabelingLogic:
    """Test safety score computation from GoPlusLabs risk signals."""

    def test_honeypot_gets_low_score(self):
        score = compute_safety_score(SAMPLE_GOPLUS_HONEYPOT)
        assert score <= 20, f"Honeypot scored too high: {score}"

    def test_safe_token_gets_high_score(self):
        score = compute_safety_score(SAMPLE_GOPLUS_SAFE)
        assert score >= 70, f"Safe token scored too low: {score}"

    def test_moderate_token_gets_middle_score(self):
        score = compute_safety_score(SAMPLE_GOPLUS_MODERATE)
        assert 30 <= score <= 80, f"Moderate token score unexpected: {score}"

    def test_known_safe_label_hint(self):
        score = compute_safety_score(SAMPLE_GOPLUS_SAFE, label_hint="safe")
        assert score == 85.0

    def test_known_scam_label_hint(self):
        score = compute_safety_score(SAMPLE_GOPLUS_HONEYPOT, label_hint="scam")
        assert score == 10.0

    def test_score_always_in_range(self):
        # Even with worst-case flags, score should be 0-100
        worst = {
            "is_honeypot": "1",
            "cannot_sell_all": "1",
            "selfdestruct": "1",
            "owner_change_balance": "1",
            "sell_tax": "1.0",
            "buy_tax": "1.0",
            "hidden_owner": "1",
            "is_proxy": "1",
            "is_mintable": "1",
            "transfer_pausable": "1",
            "is_blacklisted": "1",
        }
        score = compute_safety_score(worst)
        assert 0 <= score <= 100

    def test_high_sell_tax_reduces_score(self):
        base_score = compute_safety_score(SAMPLE_GOPLUS_SAFE)
        high_tax = {**SAMPLE_GOPLUS_SAFE, "sell_tax": "0.15"}
        tax_score = compute_safety_score(high_tax)
        assert tax_score < base_score

    def test_hidden_owner_reduces_score(self):
        base_score = compute_safety_score(SAMPLE_GOPLUS_SAFE)
        hidden = {**SAMPLE_GOPLUS_SAFE, "hidden_owner": "1"}
        hidden_score = compute_safety_score(hidden)
        assert hidden_score < base_score


class TestTokenLists:
    """Test token list integrity."""

    def test_safe_tokens_not_empty(self):
        assert len(SAFE_TOKENS) >= 20

    def test_known_scams_not_empty(self):
        assert len(KNOWN_SCAMS) >= 10

    def test_addresses_are_valid_format(self):
        for addr in list(SAFE_TOKENS.keys()) + list(KNOWN_SCAMS.keys()):
            assert addr.startswith("0x"), f"Invalid address: {addr}"
            assert len(addr) == 42, f"Wrong length: {addr}"

    def test_label_hint_safe(self):
        addr = list(SAFE_TOKENS.keys())[0]
        assert get_label_hint(addr) == "safe"

    def test_label_hint_scam(self):
        addr = list(KNOWN_SCAMS.keys())[0]
        assert get_label_hint(addr) == "scam"

    def test_label_hint_unknown(self):
        assert get_label_hint("0x0000000000000000000000000000000000000000") is None

    def test_no_overlap_between_safe_and_scam(self):
        safe_lower = {a.lower() for a in SAFE_TOKENS}
        scam_lower = {a.lower() for a in KNOWN_SCAMS}
        assert not safe_lower & scam_lower, "Safe and scam lists overlap!"
