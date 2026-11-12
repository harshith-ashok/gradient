# Gradient

An AI tutor that turns a syllabus into a personal study path for each learner.

- **Faculty** upload a syllabus (PDF, Word, text, a scan or a photo). The AI proposes topics and sub-topics, then
  drafts summaries at four levels, flashcards, quiz questions and remediation. Faculty review, edit and publish.
- **Students** take a pre-test. The AI shapes a study plan around the results, fitted inside the time frame they
  choose. Each sub-topic has a summary, flashcards and a quiz matched to their level
  (Beginner, Intermediate, Advanced, Expert). A good score moves them up; a low one keeps the level and adds
  extra material. Every attempt is saved.
- **Admins** set the pass mark (global or per course), see every student's progress, and manage users, roles, logs, errors (with stack traces) and system health.

Grading, mastery, levels and the guarantee that the whole syllabus fits the time frame are plain, tested code.
The AI proposes; the rules decide. See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the split.

**Stack:** Next.js 16, React 19, Tailwind 4 · FastAPI, SQLAlchemy, Alembic, JWT in httpOnly cookies ·
LangGraph with gpt-oss 20b (and Gemma for scanned pages) on your own Ollama server · PostgreSQL, Redis, ChromaDB · Docker.

## Run it

Prerequisites: Docker, and (for the AI parts) an Ollama server you control. Set `OLLAMA_URL` if yours is not the
default in [infra/docker-compose.yml](infra/docker-compose.yml). Without one everything works except generating
content; courses can still be written by hand.

```bash
make up          # postgres, redis, chromadb, backend, worker, frontend
open http://localhost:3000
make ai-check    # is the model server reachable and are the models installed?
```

### Demo accounts

| Portal | Account | Password | What you see |
| --- | --- | --- | --- |
| Student | `meera.iyer@gradient.edu` | `student123` | Mid-way through a plan, with a failed quiz and its reschedule |
| Student | `fatima.khan@gradient.edu` | `student123` | New student: enrol and take the pre-test |
| Faculty | `ananya.rao@gradient.edu` | `faculty123` | Upload a syllabus, review and edit, publish |
| Management | `richard.hale@gradient.edu` | `admin123` | Progress, pass mark, users, logs, issues, system |

Demo accounts exist only when `DEMO_MODE=true` (the default in development, off in production).

## Everyday commands

| Command | What it does |
| --- | --- |
| `make test` / `make lint` | Backend tests and linters |
| `make e2e` | Browser tests of the student and management journeys (stack running) |
| `make e2e-faculty` | The faculty journey, on the deterministic fake model |
| `make openapi` | Regenerate the API contract and the typed frontend client |
| `make migrate` / `make seed` | Database migrations and demo data |
| `make logs` / `make down` | Follow logs / stop the stack |

## Production

[infra/docker-compose.prod.yml](infra/docker-compose.prod.yml) publishes only the web port, requires secrets from the
environment, turns demo accounts off, marks cookies Secure and logs JSON. Put an HTTPS reverse proxy in front.

```bash
export POSTGRES_PASSWORD=...  JWT_SECRET=$(openssl rand -hex 32)  OLLAMA_URL=http://<your-server>:11434
docker compose -p gradient-prod -f infra/docker-compose.prod.yml up -d --build
docker compose -p gradient-prod -f infra/docker-compose.prod.yml exec backend \
    python -m scripts.create_user "Your Name" you@example.edu admin
make backup      # pg_dump + uploads into ./backups (keeps the newest 14)
```

Security notes: sign-in is throttled (5 failures per account and address, 30 per address, per 15 minutes, on Redis;
it fails open if Redis is down); every request gets an `X-Request-ID` that appears in the logs; every model call is
logged with its latency, token counts and outcome; uploads are size-limited and type-checked by content, not name;
the model endpoint must be your own server (models ending in `-cloud` are refused at startup).

## Repository

```
backend/    FastAPI app, agents (LangGraph), migrations, tests
frontend/   Next.js app and Playwright tests
infra/      docker-compose (dev and prod), backup script
docs/       DEVELOPMENT.md (how things work), acceptance/ (demo scenarios)
prototype/  the original Vue prototype with a mock backend, kept for reference
```

[INFO.md](INFO.md) is the product brief and [ARCHITECTURE.md](ARCHITECTURE.md) the phased plan this was built from.
