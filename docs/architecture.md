# Architecture

Maelstromhub is organized as a small monorepo with separate applications and shared packages.

## Components

- `apps/api`: FastAPI service. Owns HTTP contracts, request validation, and service orchestration.
- `apps/web`: Next.js application. Owns the browser experience, workflow screens, and API consumption.
- `apps/worker`: Background process for scheduled and queued work.
- `packages/core`: Shared Python package for domain models used by API and worker.
- `docker-compose.yml`: Local infrastructure and service orchestration.

## Local runtime

Docker Compose starts:

- Postgres for durable relational state.
- Redis for queues, caching, and lightweight coordination.
- API on port `8000`.
- Worker as a long-running background process.
- Web on port `3000`.

## Dependency direction

```text
apps/api ----\
              > packages/core
apps/worker -/

apps/web ---> apps/api over HTTP
```

The web app does not import Python packages. The API and worker may import `packages/core`, but `packages/core` should not import application code.

## Data model posture

The current repository only defines lightweight domain placeholders. Persistent schema design should be introduced with migrations once the research workflows are better specified.

## Trading posture

No component should place orders, manage keys, or call private trading APIs until the safety architecture exists. Future trading work must include explicit risk limits, audit logs, simulation coverage, and operator controls.
