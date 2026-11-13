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

## Hardening (Phase 7)

- **Sign-in throttling** (`app/core/ratelimit.py`): only wrong passwords or unknown accounts count (not a
  portal mismatch). 5 failures per account and address, 30 per address, per 15 minutes; a correct login clears
  the account counter, but a locked-out caller gets 429 even with the right password. Settings:
  `LOGIN_MAX_FAILURES`, `LOGIN_MAX_FAILURES_PER_IP`, `LOGIN_WINDOW_MINUTES`. Redis down means no throttling,
  never a failed login. `TRUST_FORWARDED_FOR=true` is set in both compose files because the browser reaches the
  API through the Next.js proxy; do not enable it when the API is exposed directly.
- **Role audit** (`tests/test_hardening.py`): the test walks every route in the OpenAPI schema and asserts it
  is 401 without a session and 403 for every role it is not meant for, so a new route without a guard fails CI.
- **Request ids and logs**: every response carries `X-Request-ID` (a caller-supplied id is kept only if it is
  8 to 64 safe characters). Set `LOG_JSON=true` for one JSON object per line with the id, status and duration.
- **Model calls**: each call logs schema, attempt, outcome (`ok`, `invalid`, `unreachable`), milliseconds and
  prompt/output token counts (`extra.llm` in JSON logs).
- **Headers and CORS**: `nosniff`, `X-Frame-Options: DENY`, referrer and permissions policies on both the API
  and the web app; API responses are `no-store`; CORS allows only the configured origin and the methods and
  headers the app uses. There is no Content-Security-Policy yet.
- **Production**: see the README. `make backup` dumps Postgres and uploads. `python -m scripts.create_user`
  makes the first admin (the demo seed does not run in production).
- **CI** runs backend tests, the contract and typecheck checks, and a browser job against the whole stack on the
  fake model (`LLM_PROVIDER=fake`). With a real model the AI planner may reorder a new student's plan, so the
  student journey is only deterministic on the fake one.

## Question sheets (Excel)

In the course editor, **Import or export questions (Excel)** (faculty who own the course, and admins):

- **Export** downloads one `.xlsx` with a row per question: Topic, Sub-topic, Level, Question, Option A to
  Option J (as many as the course needs, at least four), Correct answer (a letter), Explanation, Question ID.
  **Blank template** gives the same layout with two example rows and instructions.
- **Import** reads the same layout. Rows are matched to sub-topics by title (capitals and spacing ignored;
  Topic may be blank when the sub-topic title is unique) and to existing questions by Question ID.
  *Add and update* never deletes. *Replace* makes each sub-topic that appears in the file contain exactly the
  file's questions (matching by ID, then by identical text, so ids and history links survive); sub-topics not in the
  file are untouched. Duplicate text in a sub-topic is skipped, not added twice.
- **All or nothing.** Any bad row (unknown sub-topic, fewer than two options, repeated options, a correct answer that
  is not a filled option, a bad level or Question ID) blocks the whole import and is listed with its row number.
  **Check file** runs the same checks and shows what would change without saving.
- Safety: `.xlsx` only (not `.xls` or `.csv`), at most `MAX_UPLOAD_MB` and 5000 rows; formulas are never evaluated
  (a formula cell reads as empty) and exported text that starts with `=` is written as text.
- Imported questions are human-written, so they skip the AI's blind-answer check. Unsaved editor changes are saved
  first, because saving the editor replaces a sub-topic's questions.

API: `GET /faculty/courses/{id}/questions.xlsx`, `GET /faculty/questions/template.xlsx`,
`POST /faculty/courses/{id}/questions/import` (multipart: `file`, `mode`, `dry_run`).

## Rendering code in quizzes and study material

Question text, options, explanations, flashcards, summaries and remediation are **Markdown**: a fenced block
(```c on its own line, code, closing ```) renders as a syntax-highlighted code block, `backticks` as inline code. Raw HTML is never
rendered, images are dropped and only http(s)/mailto links survive (`components/Rich.tsx`). Quiz options render
inline so they stay valid inside a button. The AI question prompt asks for fenced code with real line breaks, the
faculty question editor has a "Preview as a student sees it", and Excel sheets carry the same Markdown. Programming
questions whose options differ only in punctuation (`i++` / `i--`) are no longer rejected as duplicates.

## Coding challenges (LeetCode-style, run in a Docker sandbox)

Faculty add challenges to a sub-topic in the course editor: statement (Markdown), languages (C, C++, Python),
starter code, time and memory limits, and tests (stdin and expected stdout; mark some as *sample*, the rest stay
hidden). "Check the tests with a reference solution" runs a solution against every test with full detail.
Students open the challenge from the sub-topic page, write code in an editor (drafts are kept in the browser),
**Run samples** (sample tests only, not counted) or **Submit** (all tests; counts as an attempt, `Solved` on
Accepted). Output is compared ignoring line endings, trailing spaces and trailing blank lines. Hidden tests only ever
report pass or fail: their input, expected output and the program's output are never sent to students.
Coding challenges do not change mastery or the study plan; they are practice.

```
POST /student/problems/{id}/submit        → submission id (queued)       judge: python -m app.judge
GET  /student/submissions/{id}            → state, verdict, per-test results (poll)
```

**How student code is contained** (`backend/sandbox/runner.py`, `app/services/judge.py`). The `judge` service claims
queued submissions and starts one throwaway container from the `gradient-sandbox` image for each:

- no network (`network_mode: none`), memory and swap capped, one CPU, at most 128 processes, `no-new-privileges`,
  Docker's default seccomp profile, all capabilities dropped except those the runner needs to switch user and stop
  the student's process; filesystem writes only to small size-capped tmpfs mounts; the container is deleted afterwards;
- the tests are sent in a file the runner reads and deletes *before* any student code runs; student code runs as
  `nobody`, with CPU time, file size, open files and process limits and a wall-clock timeout, and cannot read the
  runner or its memory;
- a per-user limit of one active run and `SUBMISSIONS_PER_MINUTE` (default 10); code is limited to `MAX_CODE_BYTES`.

`make sandbox-test` (and a CI job) check these properties against real Docker: unprivileged uid, no network, hidden
tests unreadable, filesystem read-only for the student, and infinite loops, fork bombs, memory bombs and output
floods contained. **The judge needs the Docker socket**, which is host-level power. Only the `judge` service has
it, and it only starts the fixed image with the fixed configuration above; the API and worker never touch Docker. In
production the judge is opt-in (`docker compose --profile coding up`); consider gVisor (`SANDBOX_RUNTIME=runsc`) for
an extra kernel boundary. Do not run it on a machine you would not trust with a student's code; for a shared
production host prefer a dedicated one. Without the judge running, submissions finish as "The code runner is
unavailable" and System shows the code runner as down. Dev and tests can use `JUDGE_BACKEND=local`, which runs code
as a plain subprocess with no isolation and is refused outside `ENV=dev`.

## Admin tools

Sign in as an admin. The top bar has **Users**, **Roles & endpoints**, **Logs**, **Issues** and **System**
next to the student progress and pass mark pages.

- **Users** (`/admin/users`): search and filter, create an account, change a role, deactivate or reactivate,
  reset a password. A deactivated user is signed out at once. You cannot change your own role, deactivate
  yourself, or remove the last active admin. Accounts are never hard-deleted from the UI (that would take
  their quiz history with them); deactivate instead.
- **Roles & endpoints** (`/admin/access`): the three roles are fixed (they are a database constraint). The
  endpoint table is built from the real route guards, so it cannot drift from what the server enforces, and
  shows calls, 4xx, 5xx and response times per route for the last 24 hours.
- **Logs** (`/admin/logs`): every API request (method, route, status, time, who) plus warnings and errors from
  the API and the AI worker, and an audit trail of admin changes. Filter by text, path, request id, level,
  status, source and time; "Live" refreshes every 5 seconds. Request ids match the `X-Request-ID` header and
  the JSON logs, so a user's error report leads straight to its lines.
- **Issues** (`/admin/issues`): unhandled exceptions grouped by type and the file and function that raised
  them, with the stack trace of the latest 25 occurrences, the request and user for each, a status (open,
  resolved, ignored) and a note. A resolved issue reopens by itself if it happens again. A crash in a request
  returns only `{"detail", "request_id"}` to the caller; the trace stays in the dashboard.
- **System** (`/admin/system`): Postgres and Redis state, a button to check the model server, the AI job queue
  and failed jobs with their reasons, and a 24-hour traffic chart.

What is stored: method, route template, status, duration, request id and user id. Never request bodies,
query strings, headers or cookies. Exception text is scrubbed of password hashes, tokens and `password=`
style values before saving. Rows older than `LOG_RETENTION_DAYS` (default 14) are deleted. Saving a log row
can never fail a request: errors writing to the log go to stderr only. Health checks and the session
check the web app makes on every page are not stored.

`python -m scripts.delete_users e2e-` (dev only) removes accounts by email prefix; the admin browser test uses it.
