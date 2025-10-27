PYTHON ?= python
PIP ?= $(PYTHON) -m pip
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.DEFAULT_GOAL := help

.PHONY: help install install-dev backend-install backend-install-dev frontend-install frontend-install-ci \
        up down backend-dev frontend-dev revision upgrade fmt lint test cov

# ==== HELP ====
help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install                Install prod deps for backend & frontend"
	@echo "  install-dev            Install dev deps for backend & frontend"
	@echo "  backend-dev            Run FastAPI dev server (uvicorn :8000)"
	@echo "  frontend-dev           Run Next.js dev server (:3000)"
	@echo "  up                     Start infra (db, redis) with Docker"
	@echo "  down                   Stop all Docker services"
	@echo "  revision               Create Alembic revision (use message=\"...\")"
	@echo "  upgrade                Apply Alembic migrations to head"
	@echo "  fmt                    Format code (backend + frontend)"
	@echo "  lint                   Lint code (backend + frontend)"
	@echo "  test                   Run backend tests (pytest)"
	@echo "  cov                    Run backend tests with coverage"
	@echo ""

# ==== INSTALL ====
install:
	$(PIP) install -r requirements.txt
	cd $(FRONTEND_DIR) && npm install

install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	cd $(FRONTEND_DIR) && (npm ci || npm install)

# ==== RUNTIME ====
up:
	docker compose up -d db redis

down:
	docker compose down

backend-dev:
	uvicorn $(BACKEND_DIR).app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

# ==== DATABASE ====
revision:
	@if not defined message (echo Usage: make revision message="create users table" && exit /b 1)
	alembic -c $(BACKEND_DIR)/alembic.ini revision --autogenerate -m "$(message)"

upgrade:
	alembic -c $(BACKEND_DIR)/alembic.ini upgrade head

# ==== QUALITY ====
fmt:
	$(PYTHON) -m black $(BACKEND_DIR)
	$(PYTHON) -m ruff check $(BACKEND_DIR) --fix
	cd $(FRONTEND_DIR) && npm run format

lint:
	$(PYTHON) -m black $(BACKEND_DIR) --check
	$(PYTHON) -m ruff check $(BACKEND_DIR)
	cd $(FRONTEND_DIR) && npm run lint

# ==== TESTS ====
test:
	$(PYTHON) -m pytest

cov:
	$(PYTHON) -m pytest --cov=$(BACKEND_DIR)/app --cov-report=term-missing --cov-report=xml
