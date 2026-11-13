COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: up down logs db migrate seed test e2e e2e-faculty backup openapi lint worker judge sandbox sandbox-test ai-check
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
e2e-faculty: ## faculty journey on the fake model (restarts the stack with LLM_PROVIDER=fake, then back)
	LLM_PROVIDER=fake docker compose -p gradient -f infra/docker-compose.yml up -d backend worker
	sleep 8
	cd frontend && E2E_FAKE_AI=1 npx playwright test faculty-journey; code=$$?; cd .. && docker compose -p gradient -f infra/docker-compose.yml up -d backend worker; exit $$code
backup:    ## dump Postgres and uploads of the production stack to ./backups
	infra/backup.sh gradient-prod infra/docker-compose.prod.yml
worker:    ## run the AI job worker locally (needs `make db`)
	cd backend && uv run python -m app.worker
sandbox:   ## build the image student code runs in
	docker build -t gradient-sandbox backend/sandbox
sandbox-test: sandbox  ## check the sandbox's isolation against real Docker (no network, unprivileged, limits)
	cd backend && LIVE_DOCKER=1 uv run pytest tests/test_sandbox_docker.py -q
judge:     ## run the code judge locally (needs Docker and `make sandbox`)
	cd backend && uv run python -m app.judge
ai-check:  ## is the model server reachable, and are the models installed?
	cd backend && uv run python -c "from app.agents.llm import get_llm; import json; print(json.dumps(get_llm().health(), indent=2))"
lint:
	cd backend && uv run ruff check .
openapi:   ## regenerate the API contract and the typed frontend client
	cd backend && uv run python -m scripts.export_openapi
	cd frontend && npm run gen:api
