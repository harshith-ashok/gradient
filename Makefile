COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: up down logs db migrate seed test e2e openapi lint
up:        ## build and start everything
	$(COMPOSE) up --build -d
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs -f
db:        ## only the data services, for running backend/frontend locally
	$(COMPOSE) up -d postgres redis chromadb
migrate:
	cd backend && uv run alembic upgrade head
seed:
	cd backend && uv run python -m app.seed.run
test:
	cd backend && uv run pytest
e2e:       ## browser test of the student journey (needs the stack running)
	cd frontend && npm run e2e
lint:
	cd backend && uv run ruff check .
openapi:   ## regenerate the API contract and the typed frontend client
	cd backend && uv run python -m scripts.export_openapi
	cd frontend && npm run gen:api
