# Architecture

Maelstrom is intentionally split into ingestion, storage, feature computation, API, and dashboard layers.

## Backend Packages

- `hyperliquid`: typed `/info` client with retries, validation, and limiter integration
- `limiter`: central weighted token bucket with endpoint cooldowns
- `ingest`: tiered scheduler and job isolation
- `store`: database and Redis access
- `features`: deterministic research features, flags, regimes, and scoring
- `api`: REST JSON handlers

## Data Model

The database stores raw-enough market data for auditability and clean derived feature rows for fast dashboard reads.

Timescale hypertables are created when TimescaleDB is available. The same tables work as regular PostgreSQL tables otherwise.

## Failure Handling

Hyperliquid failures are isolated per job. A failed candle pull does not stop metadata ingestion. A 429 pauses the affected endpoint class rather than letting workers spam the API.

Dashboard reads use stored data and can remain useful while the upstream API is slow or rate-limiting.
