# Base Token Sentry — AI-Powered Token Safety Scanner

> **Base Token Sentry** detects honeypots, rug-pull patterns, and dangerous contract flags in ERC-20 tokens on Base — giving users an instant safety score before they trade or invest.

[![Built on Base](https://img.shields.io/badge/Built%20on-Base-0052FF?logo=coinbase)](https://base.org)
[![Live Demo](https://img.shields.io/badge/Live-token--sentry.warvis.org-brightgreen)](https://token-sentry.warvis.org)
[![Tests](https://img.shields.io/badge/Tests-95%20passing-brightgreen)](https://github.com/WooYoungSang/base-token-sentry)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)

**Live Demo:** https://token-sentry.warvis.org  
**API:** https://api-token-sentry.warvis.org/docs

---

## Problem

New tokens launch on Base every hour. Many are honeypots, rug-pulls, or have hidden dangerous functions — but there's no fast, free tool to check token safety before trading. Users lose funds to scams that could have been caught with basic contract analysis.

---

## Solution

**Base Token Sentry** analyzes any ERC-20 token contract on Base in seconds, combining on-chain contract analysis with an XGBoost ML model trained on real Base token data — assigning a 0–100 safety score with detailed risk flags.

---

## Features

| Feature | Description |
|---------|-------------|
| **F1 — Contract Analyzer** | Decodes bytecode and ABI to detect dangerous functions (blacklist, mint, pause, fee manipulation) |
| **F2 — Honeypot Detector** | Simulates buy/sell transactions to detect transfer restrictions |
| **F3 — Liquidity Checker** | Verifies liquidity pool existence, depth, and lock status |
| **F4 — Holder Analyzer** | Checks token concentration (top holders, dev wallet %) |
| **F5 — AI Safety Scorer** | XGBoost ML model (86.5% grade accuracy) + rule-based fallback with honeypot safety guard |
| **F6 — Token Watcher** | Monitor newly deployed tokens for immediate screening |

---

## ML Model Performance

| Metric | Value |
|--------|-------|
| Grade Accuracy | **86.5%** |
| R² Score | **0.924** |
| MAE | 5.90 points |
| Training data | 28 real Base tokens (GoPlusLabs) + 1,972 synthetic |
| Data source | GoPlusLabs API (Base chain 8453), Basescan |

**Safety guards built into the scorer:**
- Honeypot tokens are **always capped at score 45** regardless of ML prediction
- ML confidence < 0.30 → falls back to rule-based scoring
- Large ML/rule divergence (>20 pts) → 40/60 confidence blend

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Next.js 14 Frontend                     │
│  / (search) · /tokens · /tokens/[addr] · /watch         │
└──────────────────────┬──────────────────────────────────┘
                       │ REST (NEXT_PUBLIC_API_URL)
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                         │
│  POST /analyze/{addr} · GET /tokens · GET /tokens/{addr}│
│  GET /watch/recent · GET /health                        │
└──┬──────────────┬─────────────┬────────────┬────────────┘
   │              │             │            │
Contract      Honeypot      Liquidity    Holder
Analyzer      Detector      Checker      Analyzer
                    │
              XGBoost ML Scorer
           (GoPlusLabs real data)
                    │
             honeypot_guard → cap 45
             confidence_fallback → rule_based
                    │
               SQLite Cache
```

---

## Quick Start

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn token_sentry.api:app --reload --port 8000
pytest tests/ -v   # 95 tests
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Docker Compose

```bash
docker compose up
```

### Real Data Collection & Retrain

```bash
python -m token_sentry.ml.collect   # GoPlusLabs + Basescan
python -m token_sentry.ml.retrain   # XGBoost retrain
```

---

## API Reference

Base URL: `https://api-token-sentry.warvis.org`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze/{address}` | Analyze a token |
| `GET` | `/tokens` | List analyzed tokens (paginated) |
| `GET` | `/tokens/{address}` | Full cached analysis |
| `GET` | `/tokens/{address}/score` | Lightweight score-only |
| `GET` | `/watch/recent` | Recently detected new tokens |

### Safety Score → Grade

| Grade | Score | Description |
|-------|-------|-------------|
| **A** | 85–100 | No dangerous flags |
| **B** | 70–84 | Minor flags, generally safe |
| **C** | 55–69 | Caution advised |
| **D** | 35–54 | Significant red flags |
| **F** | 0–34 | Honeypot or confirmed scam |

### Example Response

```json
{
  "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "score": 85,
  "grade": "A",
  "is_honeypot": false,
  "scoring_method": "ml",
  "ml_confidence": 0.82,
  "disclaimer": "Safety scores are informational only, not investment advice."
}
```

Interactive docs: `https://api-token-sentry.warvis.org/docs`

---

## Tech Stack

**Backend:** Python 3.10, FastAPI, Pydantic v2, XGBoost, scikit-learn, web3.py, SQLite  
**Frontend:** Next.js 14, TypeScript, Tailwind CSS, TanStack Query, Recharts  
**Data:** GoPlusLabs API (Base chain 8453), Basescan API, Base RPC  
**Infra:** Docker, Caddy reverse proxy, self-hosted

---

## Project Structure

```
grant-base-token-sentry/
├── backend/
│   ├── src/token_sentry/
│   │   ├── analyzer.py          # Contract bytecode/ABI analysis
│   │   ├── honeypot_detector.py # Buy/sell simulation
│   │   ├── liquidity_checker.py # LP pool analysis
│   │   ├── holder_analyzer.py   # Token distribution
│   │   ├── scorer.py            # XGBoost + rule-based scorer
│   │   ├── ml/
│   │   │   ├── data_collector.py  # GoPlusLabs + Basescan
│   │   │   ├── data_processor.py  # Feature engineering
│   │   │   ├── token_lists.py     # 30 safe + 50 popular + 15 scam
│   │   │   ├── collect.py         # CLI: collect real data
│   │   │   └── retrain.py         # CLI: retrain model
│   │   ├── api.py
│   │   └── schemas.py
│   └── tests/                   # 95 pytest tests
└── frontend/
    └── src/
        ├── app/
        ├── components/
        └── lib/
```

---

## Use Cases

- **Traders**: Check any Base token before buying on a DEX
- **Security researchers**: Monitor new token deployments for scam patterns
- **DeFi protocols**: Screen tokens before listing or integrating
- **Developers**: Verify your own token passes safety checks

---

## Built for Base Ecosystem Grants

Base Token Sentry protects Base users from the most common DeFi attack vector — malicious tokens.

**Impact metrics:**
- 95 automated tests ensuring scorer reliability
- Honeypot safety guard: score hard-capped at 45 (no false negatives)
- Live data pipeline: GoPlusLabs integration for continuous model improvement
- Open API: any wallet, DEX, or bot can integrate safety checks for free

---

## Disclaimer

Safety scores are informational only, not investment advice. Always do your own research.

---

## License

MIT © 2025 Base Token Sentry Contributors
