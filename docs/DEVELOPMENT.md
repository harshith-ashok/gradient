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

## The AI pipeline
Faculty upload a syllabus; the worker turns it into a course with study material.

```
POST /faculty/syllabus             file (PDF, Word, image, text) or pasted text  → analyze job
  analyze:  read the file (scanned pages are read by the vision model) → find topics
POST /faculty/syllabus/{id}/derive faculty pick topics                           → derive job
  derive:   sub-topics + key points for each chosen topic
POST /faculty/courses/{id}/generate                                              → generate job
  generate: summary, leveled flashcards, leveled questions, remediation per sub-topic
GET  /jobs/{id}                    poll status and progress
```

- **Agents** (`backend/app/agents/`, built with LangGraph): ingest, syllabus (topics, sub-topics) and
  content. Every model reply is validated against a schema, with one repair attempt.
- **Quality gates:** malformed questions are dropped; every new question is answered by the model
  *blind* (without the key) and dropped if it disagrees; levels short of questions are retried.
- **Never silent:** content that already exists is skipped, hand-written questions are never touched,
  and `force` is required to regenerate.
- **Jobs** live in Postgres and are run by `python -m app.worker` (the `worker` compose service).
  Failures are stored on the job with a safe message.
- **Untrusted input:** syllabus text is fenced as data in every prompt, and outputs are schema-checked.

Configuration (env): `OLLAMA_URL`, `LLM_MODEL` (default `gpt-oss:20b`), `VISION_MODEL`
(`gemma4:e4b`), `EMBED_MODEL` (`nomic-embed-text`), `CHROMA_URL`, `UPLOAD_DIR`. Models ending in
`-cloud` are refused at startup so syllabus text stays on your own server.
`make ai-check` shows which models are installed.

**Embedding model:** retrieval into ChromaDB needs one (`ollama pull nomic-embed-text`). Without it
everything still works, using keyword retrieval over the syllabus instead.

Real-model smoke tests (a few minutes): `LIVE_LLM=1 uv run pytest tests/test_live_ollama.py -s`.

## What is AI, and what is plain code

| AI (drafted or proposed) | Plain code (deterministic, always has the last word) |
| --- | --- |
| Topics and sub-topics from the syllabus (faculty review) | Grading, mastery, level changes, pass-mark checks |
| Summaries (one per level), flashcards, remediation (faculty review) | Remediation and retakes when a quiz is failed |
| Quiz and pre-test questions, with explanations (faculty review) | Choosing which questions a student gets |
| Reading scanned or handwritten files (OCR) | Fitting the plan into the student's time frame |
| **Study plan**: minutes per sub-topic, order within a topic, a starting level, a one-line focus | Making sure no task is dropped and nothing runs past the deadline |

**How the study plan is made.** The student picks a time frame (7 to 90 days) and a daily study time.
Straight after the pre-test, and again after every quiz, the rules build a plan that works on its own and
a `plan` job is queued. The worker asks the model how long each unfinished sub-topic deserves (weak ones
get more), in what order, what to focus on, and, for sub-topics not yet started, a starting level. The
answer is validated and applied only to unfinished tasks:

- It can change study minutes and the order of sub-topics inside a topic. It can never add or remove a task,
  so the whole syllabus stays in the plan.
- Starting levels are clamped to what the pre-test score supports (below half the pass mark: beginner only;
  below the pass mark: beginner or intermediate; at or above it: intermediate or advanced).
- `fit_window` then makes everything finish inside the time frame: 15% of the window is kept free for
  retakes, study and remediation sessions are shortened (never below 10 minutes) when the work is too big,
  and quizzes keep their length. If even that does not fit, the plan runs over and the student is told how
  many minutes a day would cover it. Nothing is silently dropped.
- If the model is down or answers nonsense, the rule-based plan stands. Switch it off with `AI_PLANNING=false`.

**Levels follow test performance.** A sub-topic starts at *beginner*, or *intermediate* if the pre-test
score on it reached the pass mark. Each passed quiz moves the student up one level (to *expert* at most);
a failed quiz keeps the level and adds remediation. The summary and flashcards shown for a sub-topic, and
the questions asked, come from the student's current level for it (the nearest written level if one is
missing; a hand-written summary counts as beginner).

## Faculty screens

Sign in as a faculty account: **My courses** lists drafts and published courses and warns if the model
server is down. **New course from syllabus** takes a file (PDF, Word, text, scan or photo) or pasted text,
then shows live progress, lets you untick topics, drafts the sub-topics, and opens the editor. The editor
has an outline sidebar (with a per-sub-topic completeness badge), per-level summaries, flashcards, every
quiz question (text, options, correct answer, level, explanation) and remediation, plus *Generate* for one
sub-topic or the whole course, *Save*, and *Publish* / *Unpublish*. Generating never overwrites existing
text unless "Replace what is already written" is ticked.

`make e2e-faculty` runs the faculty browser test. It restarts the backend and worker with
`LLM_PROVIDER=fake` (deterministic replies, no model server), runs the test, and restarts them normally.
