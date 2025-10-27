# Nuro Pomodoro

Nuro is a full-stack Pomodoro timer that pairs a FastAPI backend (PostgreSQL + Redis) with a Next.js 15 frontend. The API exposes JWT-based authentication, timer lifecycle management, long-poll countdown endpoints, and admin summaries. The frontend consumes those APIs to offer a focused workflow with live updates.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Redis 7, PostgreSQL 16
- **Frontend:** Next.js 15 (React 18, TypeScript, ESLint, Prettier)
- **Tooling:** pytest + httpx + fakeredis, Black, Ruff, GitHub Actions, Docker Compose

## Prerequisites

- Python 3.11
- Node.js 20 (and npm 10)
- Docker + Docker Compose (for Postgres and Redis services)

## Quick Start

```bash
# Clone the repo and enter the workspace
git clone <repo-url>
cd nuro

# (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r requirements-dev.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Start Postgres + Redis
docker compose up -d db redis

# Apply database migrations
make upgrade

# Start the FastAPI dev server (port 8000)
make dev

# In another terminal run the Next.js dev server (port 3000)
make frontend-dev
```

Visit [http://localhost:3000](http://localhost:3000) to use the UI. The backend API is available at [http://localhost:8000/api](http://localhost:8000/api).

## Configuration

Copy `backend/.env.example` to `.env` (or `backend/.env`) and adjust as needed:

```
APP_NAME=Nuro
DATABASE_URL=postgresql+asyncpg://nuro:nuro@localhost:5432/nuro
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=changeme
```

The frontend reads the API origin from `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000/api`). Set it in `frontend/.env.local` if you need a different value.

## Database Migrations

Use Alembic through the `Makefile`:

```bash
# Generate a new revision
make revision message="add new table"

# Apply migrations
make upgrade
```

## Development Commands

| Command | Description |
| --- | --- |
| `make up` / `make down` | Start/stop Docker services defined in `docker-compose.yml`. |
| `make dev` | Run FastAPI with auto-reload on port 8000. |
| `make frontend-dev` | Run `npm run dev` from the frontend directory. |
| `make fmt` | Black + Ruff (fix) for backend, Prettier for frontend. |
| `make lint` | Black --check, Ruff, and `npm run lint`. |
| `make test` | Execute pytest suite. |
| `make cov` | Pytest with coverage XML + terminal report. |

## Testing

The backend test suite uses an in-memory SQLite database and `fakeredis` to avoid external dependencies. Run:

```bash
make test
make cov
```

Coverage reports are written to `coverage.xml` (Cobertura) and printed in the terminal.

## REST Client Collections

Sample request collections are available under `requests/` for the VS Code REST Client extension:

- `requests/nuro.http` – register, login, start/cancel timers.
- `requests/admin.http` – admin login and summary endpoint.

## Continuous Integration

`.github/workflows/ci.yml` installs Python + Node dependencies, runs linters, pytest with coverage, and Next.js type checks. The pipeline expects migrations and tests to pass without extra services thanks to the SQLite + fakeredis test configuration.

## Project Structure

```
backend/
  app/
    api/        # FastAPI routers
    core/       # Settings & security helpers
    models/     # SQLAlchemy models
    services/   # Timer domain logic
    schemas/    # Pydantic schemas
    utils/      # Redis helpers & rate limits
  tests/        # pytest suite
  alembic/      # migration assets
frontend/
  app/          # Next.js app directory (layout, page, hooks, components)
  public/       # Static assets
requests/       # REST Client request files
```

## Common Workflows

1. **Create an admin user**: Register via API/UI, then update `is_admin` in the database (e.g. via SQL console or Alembic seed) to unlock `/api/admin` routes.
2. **Long-poll tick endpoints**: Use `GET /api/timers/{id}/tick` with `If-None-Match` or `If-Modified-Since` headers for efficient countdown updates. `wait=true` holds the request (<= 60s) until there is a change.
3. **Batch ticks**: `POST /api/timers/batch/tick` receives a list of timer IDs and optional client ETags to minimise payload size.

## Troubleshooting

- Ensure Docker containers are running: `docker compose ps`.
- Regenerate dependencies after updating `package.json` / `requirements*.txt`.
- Delete `.ruff_cache/` and `.pytest_cache/` if you hit stale analysis issues.

## License

This project is provided as-is for demonstration and evaluation. Adapt it to your needs.
