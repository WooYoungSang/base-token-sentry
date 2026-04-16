# Base Token Sentry — AI-Powered Token Safety Scanner

> **Base Token Sentry** detects honeypots, rug-pull patterns, and dangerous contract flags in ERC-20 tokens on Base — giving users an instant safety score before they trade or invest.

[![Built on Base](https://img.shields.io/badge/Built%20on-Base-0052FF?logo=coinbase)](https://base.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)

---

## Problem

New tokens launch on Base every hour. Many are honeypots, rug-pulls, or have hidden dangerous functions — but there's no fast, free tool to check token safety before trading. Users lose funds to scams that could have been caught with basic contract analysis.

---

## Solution

**Base Token Sentry** analyzes any ERC-20 token contract on Base in seconds, detecting dangerous patterns and assigning an overall safety score with detailed flags.

---

## Features

| Feature | Description |
|---------|-------------|
| **F1 — Contract Analyzer** | Decodes bytecode and ABI to detect dangerous functions (blacklist, mint, pause, fee manipulation) |
| **F2 — Honeypot Detector** | Simulates buy/sell transactions to detect transfer restrictions |
| **F3 — Liquidity Checker** | Verifies liquidity pool existence, depth, and lock status |
| **F4 — Holder Analyzer** | Checks token concentration (top holders, dev wallet %) |
| **F5 — Safety Scorer** | Weighted scoring (0–100) → SAFE / CAUTION / DANGER / SCAM |
| **F6 — Token Watcher** | Monitor newly deployed tokens for immediate screening |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Next.js 14 Frontend                     │
│  / (search) · /tokens · /tokens/[addr] · /analyze       │
│  /watch (new token feed)                                │
└──────────────────────┬──────────────────────────────────┘
                       │ REST (NEXT_PUBLIC_API_URL)
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                         │
│  POST /analyze · GET /tokens · GET /tokens/{addr}       │
│  GET /watch · GET /health                               │
└──┬──────────────┬─────────────┬────────────┬────────────┘
   │              │             │            │
   ▼              ▼             ▼            ▼
Contract      Honeypot      Liquidity    Holder
Analyzer      Detector      Checker      Analyzer
   │              │             │            │
   └──────────────┴─────────────┴────────────┘
                        │
                   Safety Scorer
                 (SAFE/CAUTION/DANGER/SCAM)
                        │
                   SQLite Cache
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Base RPC endpoint (public: `https://mainnet.base.org`)

### Backend

```bash
cd backend
pip install -e ".[dev]"

# Run API server
uvicorn token_sentry.api:app --reload --port 8000

# Run tests
pytest tests/ -v

# Lint
ruff check .
```

### Frontend

```bash
cd frontend
npm install

# Development
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

# Production build
npm run build
npm run lint
```

### Docker Compose (full stack)

```bash
docker compose up
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## API Reference

Base URL: `http://localhost:8000`

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Analyze a token by contract address |
| `GET` | `/tokens` | List analyzed tokens (paginated) |
| `GET` | `/tokens/{address}` | Cached analysis for a token |
| `GET` | `/tokens?verdict=DANGER` | Filter by safety verdict |
| `GET` | `/watch` | Recent newly-deployed tokens |

### Safety Verdicts

| Verdict | Score Range | Description |
|---------|-------------|-------------|
| `SAFE` | 80–100 | No dangerous flags detected |
| `CAUTION` | 50–79 | Minor flags, proceed carefully |
| `DANGER` | 20–49 | Significant red flags detected |
| `SCAM` | 0–19 | Honeypot or confirmed scam pattern |

### Example Response

```json
// POST /analyze  {"address": "0x1234..."}
{
  "address": "0x1234...",
  "name": "SomeToken",
  "symbol": "SOME",
  "verdict": "DANGER",
  "score": 32,
  "flags": [
    {"flag": "HONEYPOT", "severity": "CRITICAL", "detail": "Sell simulation failed"},
    {"flag": "HIGH_OWNER_CONCENTRATION", "severity": "HIGH", "detail": "Dev holds 45% of supply"},
    {"flag": "MINT_FUNCTION", "severity": "MEDIUM", "detail": "Owner can mint unlimited tokens"}
  ],
  "liquidity_usd": 15000,
  "holder_count": 234,
  "top_holder_pct": 0.45
}
```

### Interactive Docs

Visit `http://localhost:8000/docs` for the auto-generated Swagger UI.

---

## Tech Stack

**Backend**
- Python 3.10, FastAPI, Pydantic v2
- web3.py (Base RPC, bytecode analysis)
- Honeypot simulation via eth_call
- SQLite (analysis cache)

**Frontend**
- Next.js 14, TypeScript, Tailwind CSS
- TanStack Query
- Recharts (holder distribution chart, score gauge)
- Safety badges: SAFE=green, CAUTION=yellow, DANGER=orange, SCAM=red

**Infrastructure**
- Docker Compose
- Base RPC: `https://mainnet.base.org`

---

## Project Structure

```
grant-base-token-sentry/
├── backend/
│   ├── src/token_sentry/
│   │   ├── analyzer.py          # Contract bytecode/ABI analysis
│   │   ├── honeypot_detector.py # Buy/sell simulation
│   │   ├── liquidity_checker.py # LP pool analysis
│   │   ├── holder_analyzer.py   # Token distribution analysis
│   │   ├── scorer.py            # Safety scoring engine
│   │   ├── watcher.py           # New token monitor
│   │   ├── api.py               # FastAPI application
│   │   └── schemas.py           # Pydantic models
│   └── tests/                   # pytest test suite
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # TokenSearch, SafetyScoreGauge, etc.
│   └── lib/                     # API client, types
└── docker-compose.yml
```

---

## Use Cases

- **Traders**: Check any token before buying on DEX
- **Developers**: Verify your own token passes safety checks
- **Security researchers**: Monitor new token deployments for scams
- **DeFi protocols**: Screen tokens before listing or integrating

---

## Safety & Disclaimers

- Token safety analysis is based on heuristic patterns and is not guaranteed to be complete
- A SAFE verdict does not guarantee a token is risk-free
- Always do your own research before trading any token
- Not financial advice

---

## Built for Base Builder Grants

Base Token Sentry protects Base users from the most common DeFi attack vector — malicious tokens. By making safety analysis fast, free, and accessible, we reduce scam losses and improve user confidence in the Base ecosystem.

---

## License

MIT © 2024 Base Token Sentry Contributors

---

*Built with ❤️ on Base*
