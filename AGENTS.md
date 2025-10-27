# Agents Guide

Welcome to **Nuro**. This short guide explains the standards and workflows expected of automation or human agents working inside the repository.

## Mission Overview

- **Goal:** Deliver and maintain a Pomodoro web application.
- **Backend:** FastAPI + SQLAlchemy + Redis + PostgreSQL.
- **Frontend:** Next.js 15 (React 18, TypeScript).
- **Tooling:** Makefile driven tasks, Docker Compose for services, pytest/fakeredis for tests, ESLint/Prettier for UI.

## Daily Workflow

1. **Install deps**
   - Backend: `pip install -r requirements-dev.txt`
   - Frontend: `npm install --prefix frontend`
2. **Run services**
   - `docker compose up -d db redis`
3. **Apply migrations**
   - `make upgrade`
4. **Launch apps**
   - API: `make dev`
   - UI: `make frontend-dev`

## Validation Checklist

Run in project root before opening a PR:

```bash
make fmt        # optional auto-fix (black + ruff + prettier)
make lint       # backend + frontend lint
make test       # pytest suite (fakeredis + sqlite)
make cov        # pytest with coverage reports
npm run typecheck --prefix frontend
```

CI (`.github/workflows/ci.yml`) runs the same commands. Match its results locally.

## Key Directories

```
backend/app        FastAPI application (api, core, models, services, schemas)
backend/tests      pytest suite using fakeredis + sqlite
backend/alembic    Alembic config and migration scripts
frontend/app       Next.js pages/components/hooks/API client
requests           REST Client collections for manual API checks
.vscode            Editor tasks, launch configs, ESLint workspace hints
```

## Coding Standards

- **Python:** Match Black + Ruff settings (`pyproject.toml`). Prefer async SQLAlchemy patterns already in use.
- **TypeScript/React:** Follow ESLint (Next core web vitals) rules. `useTimer` hook controls countdown logic; reuse it instead of duplicating state.
- **Redis Keys:** Respect `nuro:timer:{id}` schema and finish lock semantics when touching timer services.
- **Testing:** Keep fakeredis/SQLite test strategy. Patch external dependencies via fixtures.

## Helpful Commands

| Task | Command |
| ---- | ------- |
| Create migration | `make revision message="add table"` |
| Upgrade DB | `make upgrade` |
| Start dependencies | `make up` |
| Stop dependencies | `make down` |
| Run frontend lint only | `npm run lint --prefix frontend` |

## Style & Docs

- Update `README.md` when workflow changes.
- Add API examples to `requests/*.http` for new endpoints.
- Keep commit messages scoped and descriptive (e.g., `feat: add batch tick endpoint`).

## Support

- Credentials live in `backend/.env.example`. Copy to `.env` locally.
- For rate-limit tweaks, adjust `RATE_LIMIT_*` in settings and `.env`.
- Need to reset Redis/Postgres during dev? `docker compose down -v` clears volumes.

> **Remember:** Run the full validation checklist before pushing. It keeps the automation happy and CI green.

