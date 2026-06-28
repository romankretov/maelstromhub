# Product Vision

Maelstromhub is a streamlined quant trading and research suite for Hyperliquid. The first phase focuses on disciplined research workflows, transparent data handling, reproducible experiments, and operational clarity before any trading execution is introduced.

## Target users

- Quant researchers validating ideas against market data.
- Engineers building reliable data and job infrastructure.
- Operators reviewing system health, research outputs, and future trading controls.

## Product principles

- Research first: prioritize repeatable experiments, clean assumptions, and visible provenance.
- Safety before execution: do not ship trading paths until risk controls, auditability, and kill switches are designed.
- Fast local feedback: every app should be easy to run locally with Docker Compose.
- Clear boundaries: keep domain models shared, service concerns local, and interfaces explicit.

## Initial scope

- API shell for health checks and future research endpoints.
- Web shell for status and workflow surfaces.
- Worker shell for background jobs.
- Shared Python domain models.
- Local Postgres and Redis infrastructure.

## Explicitly out of scope

- Live trading.
- Order placement.
- Private key handling.
- Strategy recommendations.
- Production deployment automation.
