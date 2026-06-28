# Maelstromhub

A streamlined quant trading and research suite for Hyperliquid.

This repository is intentionally a clean foundation. It provides the API, web app, worker, shared Python domain package, local infrastructure, and project documentation. Trading execution is not implemented yet.

## Repository layout

```text
apps/
  api/       FastAPI service
  web/       Next.js app with TypeScript, Tailwind, and shadcn/ui conventions
  worker/    Background job process
packages/
  core/      Shared Python domain models
docs/        Product, architecture, roadmap, and standards
```

## Requirements

- Docker and Docker Compose
- Node.js 20+ and npm 10+ for local web development outside Docker
- Python 3.12+ for local API or worker development outside Docker

## Run locally with Docker

```bash
cp .env.example .env
npm run dev
```

Services:

- Web: http://localhost:3000
- API: http://localhost:8000
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

Run database migrations and seed local workflow data:

```bash
docker compose exec api alembic -c alembic.ini upgrade head
docker compose exec api python -m scripts.seed
```

Stop the stack:

```bash
npm run compose:down
```

Docker dev troubleshooting:

- After Dockerfile or dependency changes, reset and rebuild with:

  ```bash
  docker compose down -v
  docker compose build --no-cache
  docker compose up
  ```

- The API container runs from `/app/apps/api` with `PYTHONPATH=/app/apps/api:/app/packages/core`, so `uvicorn app.main:app` imports the bind-mounted API package during development.
- The worker container runs from `/app/apps/worker` with `PYTHONPATH=/app/apps/worker:/app/apps/api:/app/packages/core`, so `python -m worker.main` can import both the worker and API repository modules.
- On Fedora and other SELinux-enabled hosts, bind mounts may otherwise show up as `EACCES` inside containers. The Compose file uses shared `:z` relabeling on source bind mounts so the web container can read `apps/web/package.json` and Python containers can read mounted source. Shared relabeling is intentional because `apps/api` and `packages/core` are mounted into more than one service.
- The web container runs npm from `/app` using the workspace command and keeps `node_modules` plus `.next` on Docker-managed volumes. If dependencies or generated Next files get into a bad state, `docker compose down -v` recreates those volumes.

## Run pieces locally

Web:

```bash
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev:web
```

API:

```bash
docker compose up postgres redis
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e ../../packages/core -e ".[dev]"
alembic -c alembic.ini upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

The first supported workflow is:

```text
Ideas Lab: create idea -> Strategy Builder: create Draft strategy
```

Research datasets use system-defined exchange timeframes. The API seeds these automatically on startup and the seed script also repairs them if needed:

```text
1m, 5m, 15m, 1h, 4h, 1d
```

End users should create assets and datasets; they should not create regular exchange timeframes manually. The `/timeframes` API remains available as an internal/admin surface for inspecting supported intervals.

Local database reset:

```bash
npm run compose:down
docker volume rm maelstromhub_postgres-data
npm run dev
```

UUID schema notes:

- Generated entity identifiers are native PostgreSQL `uuid` columns, not `varchar`: every generated primary key named `id` and every generated foreign key named `*_id` uses UUID storage.
- `strategy_templates.id` is also a UUID primary key. The built-in templates use stable UUIDs and keep their strategy behavior selected in application code.
- Alembic revisions now create UUID columns directly. Revision `0010_repair_uuid_columns` repairs existing PostgreSQL databases by converting legacy varchar ID columns to UUID and remapping old template slugs to their stable UUIDs.
- API responses still serialize UUID values as strings, so frontend route construction and JSON payloads remain string-based at the transport boundary.

Worker:

```bash
cd apps/worker
python -m venv .venv
. .venv/bin/activate
pip install -e ../../packages/core -e ".[dev]"
python -m worker.main
```

## Development notes

- Keep domain objects that are shared by API and worker in `packages/core`.
- Keep service runtime concerns inside `apps/api` and `apps/worker`.
- Use the docs in `docs/` as the working product and architecture baseline.
- Do not add trading execution paths until the research, safety, and audit model is designed.
