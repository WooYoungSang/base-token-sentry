"""Tests for Token Sentry FastAPI endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from token_sentry.models import (
    ContractAnalysis,
    HolderAnalysis,
    HoneypotResult,
    LiquidityAnalysis,
    SafetyScore,
)

ADDR = "0x1234567890123456789012345678901234567890"
ADDR2 = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"

# Override DB to temp path before importing app
import tempfile  # noqa: E402

import token_sentry.api as api_module  # noqa: E402

_tmp_db = tempfile.mktemp(suffix=".db")
api_module.DB_PATH = Path(_tmp_db)

from token_sentry.api import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Reset DB before each test."""
    if Path(_tmp_db).exists():
        Path(_tmp_db).unlink()
    api_module._init_db()
    yield
    if Path(_tmp_db).exists():
        Path(_tmp_db).unlink()


@pytest.fixture
def client():
    return TestClient(app)


def _make_safe_score(address: str = ADDR) -> SafetyScore:
    contract = ContractAnalysis(address=address, verified_source=True)
    holder = HolderAnalysis(address=address, top10_concentration=0.3, whale_percentage=0.1)
    liquidity = LiquidityAnalysis(address=address, total_liquidity_usd=100_000, lp_locked=True)
    honeypot = HoneypotResult(address=address, is_honeypot=False, sell_tax=0.01)
    from token_sentry.scorer import SafetyScorer
    return SafetyScorer().score(address, contract, holder, liquidity, honeypot)


def _make_honeypot_score(address: str = ADDR) -> SafetyScore:
    contract = ContractAnalysis(address=address, has_blacklist=True, has_owner_blacklist=True,
                                risk_flags=["owner_blacklist"])
    holder = HolderAnalysis(address=address, whale_percentage=0.7, single_holder_dominant=True)
    liquidity = LiquidityAnalysis(address=address, total_liquidity_usd=500, low_liquidity=True)
    honeypot = HoneypotResult(address=address, is_honeypot=True, sell_tax=0.95)
    from token_sentry.scorer import SafetyScorer
    return SafetyScorer().score(address, contract, holder, liquidity, honeypot)


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestAnalyze:
    def test_analyze_returns_score(self, client):
        score = _make_safe_score()
        with patch.object(api_module, "_run_analysis", AsyncMock(return_value=score)):
            resp = client.post(f"/analyze/{ADDR}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["address"] == ADDR
        assert 0 <= data["score"] <= 100
        assert data["grade"] in ("A", "B", "C", "D", "F")
        assert "disclaimer" in data

    def test_analyze_cached_on_second_call(self, client):
        score = _make_safe_score()
        with patch.object(api_module, "_run_analysis", AsyncMock(return_value=score)) as mock_run:
            client.post(f"/analyze/{ADDR}")
            client.post(f"/analyze/{ADDR}")
        # Second call should use cache — analysis runs once
        mock_run.assert_called_once()

    def test_analyze_honeypot_flagged(self, client):
        score = _make_honeypot_score()
        with patch.object(api_module, "_run_analysis", AsyncMock(return_value=score)):
            resp = client.post(f"/analyze/{ADDR}")
        assert resp.status_code == 200
        assert resp.json()["is_honeypot"] is True

    def test_analyze_analysis_failure_returns_500(self, client):
        with patch.object(api_module, "_run_analysis", AsyncMock(side_effect=Exception("rpc error"))):
            resp = client.post(f"/analyze/{ADDR}")
        assert resp.status_code == 500


class TestTokenList:
    def _seed(self, client):
        safe = _make_safe_score(ADDR)
        hp = _make_honeypot_score(ADDR2)
        with patch.object(api_module, "_run_analysis", AsyncMock(side_effect=[safe, hp])):
            client.post(f"/analyze/{ADDR}")
            client.post(f"/analyze/{ADDR2}")

    def test_list_returns_tokens(self, client):
        self._seed(client)
        resp = client.get("/tokens")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["tokens"]) == 2
        assert "disclaimer" in data

    def test_filter_by_honeypot(self, client):
        self._seed(client)
        resp = client.get("/tokens?is_honeypot=true")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["is_honeypot"] for t in data["tokens"])

    def test_filter_by_grade(self, client):
        self._seed(client)
        resp = client.get("/tokens?grade=A")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["grade"] == "A" for t in data["tokens"])

    def test_pagination(self, client):
        self._seed(client)
        resp = client.get("/tokens?page=1&page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tokens"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1


class TestTokenDetail:
    def test_get_token_detail(self, client):
        score = _make_safe_score()
        with patch.object(api_module, "_run_analysis", AsyncMock(return_value=score)):
            client.post(f"/analyze/{ADDR}")
        resp = client.get(f"/tokens/{ADDR}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["address"] == ADDR
        assert "contract" in data
        assert "honeypot" in data
        assert "disclaimer" in data

    def test_get_token_not_found(self, client):
        resp = client.get(f"/tokens/{ADDR}")
        assert resp.status_code == 404

    def test_get_token_score_lightweight(self, client):
        score = _make_safe_score()
        with patch.object(api_module, "_run_analysis", AsyncMock(return_value=score)):
            client.post(f"/analyze/{ADDR}")
        resp = client.get(f"/tokens/{ADDR}/score")
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "grade" in data
        assert "penalties" in data
        assert "disclaimer" in data
        # Should NOT have contract/holder/etc (lightweight)
        assert "contract" not in data

    def test_get_score_not_found(self, client):
        resp = client.get(f"/tokens/{ADDR}/score")
        assert resp.status_code == 404


class TestRecentWatch:
    def test_recent_tokens_empty(self, client):
        resp = client.get("/watch/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tokens"] == []
        assert data["count"] == 0

    def test_recent_tokens_with_data(self, client):
        # Insert directly into recent_tokens table
        import sqlite3
        with sqlite3.connect(_tmp_db) as conn:
            conn.execute(
                "INSERT INTO recent_tokens (address, detected_at) VALUES (?, ?)",
                (ADDR, "2026-04-17T00:00:00+00:00")
            )
            conn.commit()
        resp = client.get("/watch/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["tokens"][0]["address"] == ADDR
