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

Stop the stack:

```bash
npm run compose:down
```

## Run pieces locally

Web:

```bash
npm install
npm run dev:web
```

API:

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e ../../packages/core -e ".[dev]"
uvicorn app.main:app --reload
```

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
