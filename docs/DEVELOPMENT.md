# Development

## Everything in Docker
```bash
make up        # postgres, redis, chromadb, backend (migrates + seeds), frontend
make logs
make down
```
Frontend http://localhost:3000 · API http://localhost:8010/docs · Postgres on host port 5433, Redis on 6380 (5432/6379 are often taken by local installs).

## Run backend and frontend locally
```bash
make db                                  # postgres, redis, chromadb only
cd backend && cp .env.example .env
uv sync && make -C .. migrate seed
uv run uvicorn app.main:app --port 8010 --reload
cd frontend && npm install && npm run dev
```

## Contract workflow
FastAPI is the source of truth. After changing a route or schema run `make openapi`; it rewrites
`backend/openapi.json` and `frontend/lib/api-client/schema.d.ts`. CI fails if either is stale.

## Tests
`make test` (backend, SQLite in memory) · `cd frontend && npm run typecheck && npm run lint`.

Demo accounts: see `docs/acceptance/demo-scenarios.md`.

## End-to-end test (real browser)
```bash
make up   # or: backend + `npm run dev` in frontend/
cd frontend && npx playwright install chromium   # once
npm run e2e
```
It resets the demo student Fatima (`backend/scripts/reset_student.py`, dev only), then walks the whole
journey: enrol, pre-test, study, fail a quiz, plan adapts, recover, practice, progress, sign out. Set
`CHROMIUM_PATH` to use an existing Chromium binary.

## Demo data
`python -m app.seed.run` creates users, the three courses and, once, replays eight students' study
history through the real learning service with the clock moved back (so Meera really has a failed
quiz and its reschedule). It never runs on a database that already has enrolments.
