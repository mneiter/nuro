PYTHON ?= python
PIP ?= pip
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: install install-dev frontend-install up down dev revision upgrade fmt lint test cov frontend-dev

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

up:
	docker compose up -d db redis

down:
	docker compose down

dev:
	uvicorn $(BACKEND_DIR).app.main:app --reload --host 0.0.0.0 --port 8000

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-dev: frontend-install
	cd $(FRONTEND_DIR) && npm run dev

revision:
	@if [ -z "$(message)" ]; then echo "Usage: make revision message='create users table'"; exit 1; fi
	alembic -c $(BACKEND_DIR)/alembic.ini revision --autogenerate -m "$(message)"

upgrade:
	alembic -c $(BACKEND_DIR)/alembic.ini upgrade head

fmt:
	$(PYTHON) -m black $(BACKEND_DIR)
	$(PYTHON) -m ruff check $(BACKEND_DIR) --fix
	cd $(FRONTEND_DIR) && npm run format

lint:
	$(PYTHON) -m black $(BACKEND_DIR) --check
	$(PYTHON) -m ruff check $(BACKEND_DIR)
	cd $(FRONTEND_DIR) && npm run lint

test:
	$(PYTHON) -m pytest

cov:
	$(PYTHON) -m pytest --cov=$(BACKEND_DIR)/app --cov-report=term-missing --cov-report=xml

