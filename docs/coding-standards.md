# Coding Standards

## General

- Keep changes small and scoped.
- Prefer explicit interfaces over implicit coupling.
- Put shared domain models in `packages/core`.
- Keep framework-specific code inside the owning app.
- Add tests with new behavior, especially around money, state transitions, and background jobs.

## Python

- Target Python 3.12+.
- Use type hints for public functions.
- Use Pydantic models at service boundaries and for shared domain objects.
- Keep IO at the application layer; avoid database, network, or queue clients in `packages/core`.
- Prefer structured settings via `pydantic-settings`.

## TypeScript

- Target strict TypeScript.
- Keep reusable UI primitives under `apps/web/components`.
- Keep route-level logic in the Next.js `app` directory.
- Prefer server components by default; introduce client components only for interaction.
- Use shadcn/ui conventions for component structure and styling.

## Styling

- Use Tailwind utility classes and design tokens from `globals.css`.
- Keep layouts responsive from the start.
- Avoid one-off CSS unless a component needs behavior Tailwind cannot express clearly.

## Documentation

- Update `docs/architecture.md` when component boundaries change.
- Update `docs/roadmap.md` when scope meaningfully changes.
- Keep README commands accurate and runnable.
