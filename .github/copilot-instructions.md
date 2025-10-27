## Nuro — Copilot / AI agent quick instructions

This file gives focused, actionable instructions for AI coding agents working in this repository. Keep entries short and concrete; reference the repo files when demonstrating patterns.

- Project summary: full-stack Pomodoro app. Backend is FastAPI + SQLAlchemy (async) + Redis + Postgres. Frontend is Next.js 15 (React + TypeScript).

- Quick validation (run locally before PR):

  - make fmt # format (Black/Ruff + Prettier)
  - make lint # backend + frontend lint
  - make test # pytest (uses sqlite + fakeredis)
  - make cov # coverage
  - npm run typecheck --prefix frontend

- Dev servers / common tasks:

  - Start dependencies: `docker compose up -d db redis` (see `docker-compose.yml`)
  - Apply DB migrations: `make upgrade` (Alembic; see `alembic/`)
  - Run API: `make dev` (FastAPI on :8000)
  - Run frontend: `make frontend-dev` (Next dev on :3000)

- Important file locations to reference in edits:

  - backend/app/api/timers.py — timer endpoints including `GET /api/timers/{id}/tick` and `POST /api/timers/batch/tick`
  - backend/app/services/timers.py — domain logic for timer lifecycle
  - backend/app/utils/redis.py — Redis key templates (TIMER_KEY_TEMPLATE and finish-lock)
  - backend/app/models/timer.py — SQLAlchemy model shapes
  - backend/app/core/config.py, core/security.py — app settings / JWT behavior
  - frontend/app/hooks/useTimer.ts — canonical client-side timer logic (re-use it rather than duplicating)
  - frontend/app/api/client.ts — API client; demonstrates ETag usage (If-None-Match) and long-poll pattern
  - requests/\*.http — sample REST requests useful for manual testing

- Patterns and conventions the agent must follow (concrete):

  - Async-first backend: use async SQLAlchemy patterns already in code (don't switch to sync models).
  - Redis keys: always respect `nuro:timer:{timer_id}` and `nuro:timer:{timer_id}:finish-lock` (see `backend/app/utils/redis.py`). Avoid introducing alternate key schemas.
  - Long-polling and ETags: timer ticks use ETag/If-None-Match and optional `wait=true` to hold a request (<=60s). See `backend/app/api/timers.py` and `frontend/app/api/client.ts` (longPollTimer).
  - Frontend state: `useTimer` is the single source of truth for timer UI state. Prefer updating this hook over creating new global timer stores.
  - Tests use SQLite + fakeredis — prefer adding tests that rely on these fixtures (see `backend/tests/` and `conftest.py`).

- Examples (copyable guidance):

  - When polling for timer updates, client sets header `If-None-Match: <etag>` and calls `GET /api/timers/{id}/tick?wait=true` (see `frontend/app/api/client.ts`). If server returns 304, the client should keep local state unchanged.
  - For batch polling, use `POST /api/timers/batch/tick` with timer ids and client etags to minimize payload (see `backend/app/api/timers.py`).

- Safety / Do/Don't (repo-specific):

  - DO update `backend/.env.example` when adding new env vars. Tests rely on defaults; document any required changes in `README.md`.
  - DO run `make fmt` and `make lint` before committing; CI enforces the same checks.
  - DON'T change Redis key formats or TTL semantics without updating `backend/app/utils/redis.py` and searches across repo.
  - DON'T alter timer tick semantics without adding/adjusting tests in `backend/tests/test_timers.py` that exercise the ETag and wait semantics.

- When adding endpoints or changing public API shape:

  - Add API examples to `requests/*.http`.
  - Update README quickstart and `agents.md` if the developer workflow changes.

- Contact points and short debugging tips:
  - Check running services: `docker compose ps` (Postgres/Redis)
  - Tests that fail locally often indicate missing env vars or stale migrations — run `make upgrade` and re-run tests.
  - Look at `frontend/app/hooks/useTimer.ts` for real-client usage of the API when implementing server changes.

If something in this file is unclear or you want the agent to prefer different behaviors (more strict linting, different test strategy), say so and I will update this file.
