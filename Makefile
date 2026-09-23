.PHONY: setup setup-db migrate seed dev dev-api dev-web test

setup:
	@echo "Starting PostgreSQL + pgvector..."
	docker compose up -d
	@echo "Installing backend dependencies..."
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

setup-db:
	cd backend && ./venv/bin/alembic upgrade head

seed:
	cd backend && ./venv/bin/python -m app.seed.seeder

dev-api:
	cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

test:
	cd backend && ./venv/bin/pytest tests/ -v
