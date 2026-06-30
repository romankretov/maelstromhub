# Maelstrom Hyperliquid Research Engine

Maelstrom is a research-opportunity discovery engine for Hyperliquid perpetual markets.

It is not a trading platform. It does not include execution, wallets, strategy deployment, notebooks, or backtesting.

The primary product question is:

> Which Hyperliquid perps deserve research attention today, and why?

## Stack

- Backend: Go REST API and ingestion scheduler
- Database: PostgreSQL, with TimescaleDB hypertables when the extension is available
- Cache: Redis for latest-state caching and future stale-data serving
- Frontend: Next.js + TypeScript
- Charts: ECharts
- Local deployment: Docker Compose

## Run

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- Backend: http://localhost:8080
- Health: http://localhost:8080/health

On startup the backend runs SQL migrations, starts the scheduler, and begins loading Hyperliquid market data.

## Config

See [deploy/env.example](deploy/env.example).

Important settings:

- `HYPERLIQUID_BASE_URL`
- `POSTGRES_DSN`
- `REDIS_URL`
- `RATE_LIMIT_WEIGHT_PER_MINUTE`
- `ENDPOINT_WEIGHTS`
- `TIER1_META_INTERVAL_SECONDS`
- `TIER1_MIDS_INTERVAL_SECONDS`
- `CANDLE_INTERVALS`
- `CANDLE_BACKFILL_DAYS`
- `SHORTLIST_SIZE`
- `L2BOOK_INTERVAL_SECONDS`
- `RECENT_TRADES_INTERVAL_SECONDS`
- `LOG_LEVEL`

Endpoint weights are config-driven because Hyperliquid’s official docs are the source of truth and can change.

## Architecture

The ingestion engine is tiered:

1. Tier 1: all markets, frequent
   - `metaAndAssetCtxs`
   - `allMids`
   - stores `markets` and `market_snapshots`
2. Tier 2: candles, slower
   - `candleSnapshot`
   - idempotent candle upserts
3. Tier 3: enrichment, shortlist-only
   - designed for `l2Book`, `recentTrades`, and `fundingHistory`
   - rate-budget aware and safe to defer

The weighted limiter prevents uncontrolled API usage. On 429 it pauses the endpoint class, applies exponential cooldown, logs the event, and lets the dashboard continue serving already stored data.

## API

- `GET /health`
- `GET /api/markets`
- `GET /api/markets/{coin}`
- `GET /api/markets/{coin}/candles?interval=5m&from=&to=`
- `GET /api/flags`
- `GET /api/ingestion/status`
- `GET /metrics`

## Dashboard

Pages:

- Market Scanner: ranked perps by research score
- Coin Detail: chart, feature cards, flags, suggested research direction
- Ingestion Health: jobs, limiter metrics, failures, 429 count, queue depth

## Research Score

Initial score:

```text
research_score =
0.25 * liquidity_score +
0.20 * oi_anomaly_score +
0.20 * volume_anomaly_score +
0.15 * momentum_score +
0.10 * funding_anomaly_score +
0.10 * execution_quality_score
```

Regime labels:

- `trend_candidate`
- `momentum_candidate`
- `mean_reversion_candidate`
- `squeeze_candidate`
- `volatility_breakout_candidate`
- `ignore_low_liquidity`
- `ignore_choppy`

## Reliability Notes

Implemented:

- context-aware Hyperliquid requests
- typed client structs
- exponential retry with jitter
- weighted rate limiter
- 429 endpoint cooldown
- idempotent market/candle/feature writes
- ingestion run tracking
- job locks
- structured JSON logs
- graceful shutdown
- unit tests for client parsing, limiter behavior, and feature calculations

Planned next:

- richer L2/recent trade/funding enrichment workers
- Prometheus metrics
- stale-data warning thresholds per endpoint
- historical backfill planner that tracks exact covered ranges
