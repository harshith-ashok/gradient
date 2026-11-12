# Gradient: Phased Architecture and Conversion Plan

Goal: turn the working prototype (`prototype/`: Vue 3 + a mock JS backend over `localStorage`) into the system described in [INFO.md](INFO.md): Next.js, FastAPI, PostgreSQL, Redis, ChromaDB, LangGraph with gpt-oss 20b and Gemma, all in Docker.

## 1. What we are converting

| Prototype piece | Real-system replacement | Conversion effort |
| --- | --- | --- |
| `src/views`, `src/components` (Vue) | Next.js App Router + React + Tailwind | Rewrite (same screens, same design tokens) |
| `src/backend/index.js` (`api.auth/student/faculty/admin`) | FastAPI routers, OpenAPI contract | Becomes the API spec |
| `services/auth.js`, `hash.js` | JWT auth, argon2/bcrypt, RBAC dependencies | Rewrite properly |
| `services/planner.js` (pure functions) | Python module, same logic | Direct port, keep deterministic |
| `services/learning.js` (grading, mastery, adaptive rules) | Python service layer | Direct port, keep deterministic |
| `services/metrics.js`, `settings.js`, `courses.js` | SQL queries + services | Port to SQLAlchemy |
| `services/syllabus.js` (rule-based) | LangGraph syllabus agent | Replace with LLM |
| `services/contentgen.js` (templated) | LangGraph content agent (summary, flashcards, quiz, remediation) | Replace with LLM |
| `db.js` (document store) + `seed.js` | PostgreSQL schema + Alembic + seed script | Redesign as relational |
| `data/course-*.js` | Seed fixtures (C, C++, Economics) | Keep as seed data |

Key principle: **the adaptive logic stays rule-based code, not an LLM.** Mastery updates, pass-mark checks, rescheduling and plan repacking must be deterministic and testable. The LLM only produces content (topics, summaries, flashcards, questions, remediation).

## 2. Target architecture

```
Browser ── Next.js (SSR/CSR, Tailwind)
              │  REST + JWT (httpOnly cookie)
              ▼
          FastAPI  ───────────────┬────────────────┐
   routers → services → repos     │                │
              │                   ▼                ▼
              │            Redis (cache,     Worker (ARQ/Celery)
              │            rate limit,        runs LangGraph jobs
              │            job queue)               │
              ▼                                     ▼
        PostgreSQL                     LangGraph agents
   (users, courses, plans,            ├─ ingest: parse PDF/DOCX, OCR (Gemma)
    attempts, settings)               ├─ syllabus → topics → sub-topics
        ChromaDB ◄────────────────────├─ content: summary, flashcards, quiz
   (syllabus chunks, embeddings)      └─ remediation
                                              │
                                   gpt-oss 20b (Tailscale Ollama)
                                   Gemma (scanned / handwritten input)
```

Backend layers: `api/` (routers, schemas) → `services/` (business logic, ported from prototype) → `repos/` (SQLAlchemy) → `agents/` (LangGraph). Long-running AI work runs in a worker, never in a request handler.

### Data model (PostgreSQL)

- `users` (id, name, email, password_hash, role: student|faculty|admin)
- `courses` (id, title, owner_id, status: draft|published, pass_mark nullable)
- `topics` (course_id, position, title, summary) and `subtopics` (topic_id, position, title, key_points, summary, level)
- `flashcards`, `questions` (subtopic_id, level, type, options, answer, explanation), `remediation_items`
- `syllabus_uploads` (course_id, file ref, status, extracted_text, agent_run_id)
- `enrollments` (user_id, course_id, minutes_per_day, level per topic)
- `pretest_results`, `mastery` (enrollment_id, subtopic_id, score, level, needs_review)
- `plan_tasks` (enrollment_id, subtopic_id, type: study|quiz|remediation|topic_quiz, day, status, position)
- `quiz_attempts` (every attempt, score, answers JSONB, passed, created_at) — the full history INFO.md requires
- `settings` (global pass mark; per-course override lives on `courses`)

Levels (Beginner → Expert) live on `mastery` and `questions`; content is generated per level and cached.

### API surface

Mirror the prototype's `api` object one to one, grouped by role:

- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- Student: `/student/dashboard`, `/catalog`, `/courses/{id}`, `/subtopics/{id}`, `POST /quizzes`, `POST /quizzes/{id}/submit`, `/plan`, `/progress`, `/practice`
- Faculty: `/faculty/courses`, `POST /courses/{id}/syllabus` (returns a job id), `GET /jobs/{id}`, `PUT /courses/{id}`, `POST /courses/{id}/publish`
- Admin: `/admin/students`, `/admin/students/{id}`, `/admin/settings`

FastAPI generates OpenAPI; the Next.js client is generated from it so the two sides cannot drift.

## 3. Phases

Each phase ends with something runnable and a clear exit check. Nothing is deleted from `prototype/` until the replacement passes the same demo scenarios.

### Phase 0: Foundation and contract (1 week)

1. Create `backend/`, `frontend/`, `infra/` beside `prototype/`.
2. `docker-compose.yml`: postgres, redis, chromadb, backend, frontend. One `make up`.
3. Write the API contract (OpenAPI) from `prototype/src/backend/index.js` before writing handlers.
4. Backend skeleton: FastAPI app, settings via env, SQLAlchemy 2 + Alembic, pytest, ruff, CI.
5. Frontend skeleton: Next.js (TypeScript), Tailwind configured with the prototype's tokens from `style.css` (`--paper`, `--surface`, crimson accent, Spectral + Public Sans), generated API client.
6. Extract the prototype's demo scenarios into a written checklist (Meera mid-plan with a failed quiz, Fatima new student, etc.). These are the acceptance tests for every later phase.

Exit: `make up` brings up all services; `/health` and the frontend home page work.

### Phase 1: Auth, roles, core schema (1 week)

1. Alembic migrations for the full schema above.
2. JWT auth (access + refresh, httpOnly cookies), argon2 hashing, role dependencies (`require_role`).
3. Port `auth.js` and the three portals' landing logic. Next.js middleware handles role-based redirects (replaces the vue-router guard).
4. Seed script: port `data/users.js` and `data/course-*.js` into SQL fixtures. Replace the clock-shifting trick in `seed.js` with explicit historical rows.
5. Login screens in Next.js, matching the prototype.

Exit: all four demo accounts log in and land on the right page; wrong-role access returns 403.

### Phase 2: Course and student read paths (1 to 1.5 weeks)

1. Port `courses.js`: staff list/edit/publish, student read-only structure.
2. Port the student catalog, course view, sub-topic view (summary, flashcards) using seeded content.
3. Rebuild shared components in React: `AppShell`, `RingProgress`, `MeterBar`, `TaskRow`, `FlashcardDeck`, `LoadState`, toast.
4. Redis cache for published course structure (invalidate on publish).

Exit: a student can browse C, C++ and Economics down to flashcards, backed by Postgres.

### Phase 3: Learning engine (adaptive logic) (1.5 weeks)

The core of the product. Port, don't redesign.

1. Port `planner.js` to `services/planner.py` (pure functions: build plan from pre-test, pack tasks into days, insert follow-ups).
2. Port `learning.js`: enrolment, pre-test, quiz start/submit, grading, mastery update, level promotion, remediation insertion, rollover of missed tasks, end-of-day status.
3. Add level handling from INFO.md: a good score moves the student up a level, a low score keeps the level and adds extra material.
4. Persist every attempt in `quiz_attempts`.
5. Port the pass mark settings (global with per-course override).
6. Unit-test the rules with table-driven tests built from the prototype's behaviour (see "How the adaptive logic works" in the README). Run the planner against property tests: no day exceeds the time budget, no task lost on repack.
7. Rebuild `QuizSession`, `PlanView`, `PracticeView`, `ProgressView` in React.

Exit: Meera and Fatima scenarios reproduce identically; failing a quiz reschedules and adds remediation.

### Phase 4: Dashboards and admin (1 week)

1. Port `metrics.js` as SQL aggregates (overall %, per-topic mastery, upcoming tasks); add indexes and a short Redis cache.
2. Admin dashboard, student detail, settings page, shared progress component.
3. Quiz attempt history view for students.

Exit: admin sees every student's progress; changing the pass mark changes outcomes of new attempts.

### Phase 5: AI pipeline with LangGraph (2 weeks)

Replace the rule-based syllabus and templated generators one agent at a time, each behind the same service interface so the rest of the app does not change.

1. **Model access**: client for gpt-oss 20b over the Tailscale Ollama endpoint (config via env, timeout, retries). Fake LLM provider for tests and CI.
2. **Ingest graph**: file → text. Text PDFs and DOCX parsed directly; scanned or handwritten files go to Gemma for OCR/transcription. Store the extracted text.
3. **Syllabus graph**: text → topics → faculty selects topics → sub-topics with key points. Structured output validated with Pydantic; one repair retry on invalid JSON. Chunks embedded into ChromaDB per course.
4. **Content graph**: per sub-topic and level, generate summary, flashcards, quiz questions (grounded in retrieved chunks from ChromaDB), then a validation node (answer is in options, no duplicates, matches level). Remediation material generated from the questions the student missed.
5. **Async execution**: endpoints return a job id; the worker runs the graph; the frontend polls `/jobs/{id}` (SSE later). Faculty review and edit the output before publish, as in the prototype.
6. Cache generated content in Postgres so a level's material is generated once.

Exit: uploading a real PDF produces a reviewable topic tree; published courses have generated, validated content.

### Phase 6: Faculty flow end to end (1 week)

1. Syllabus upload page, topic selection, and the `CourseEditor` sidebar in React, wired to the real job flow.
2. Progress and error states for long jobs; re-run a single sub-topic generation.
3. Editing individual quiz questions (listed as missing in the prototype).

Exit: faculty upload, review, edit and publish a new course, and a student can study and be graded on it.

### Phase 7: Hardening and release (1 to 1.5 weeks)

1. Security: rate limiting on login (Redis), CORS, upload size and type limits, secrets via env, audit of role checks on every route.
2. Observability: structured logs, request ids, LLM call tracing (latency, tokens, failures).
3. Tests: backend unit + API tests, a few Playwright flows covering the demo scenarios.
4. Performance: N+1 check on dashboards, pagination for the admin student list.
5. Production compose profile, backups for Postgres, README with setup and demo accounts.
6. Remove `prototype/` or keep it as a design reference tagged in git.

Exit: clean install from the README works; the Playwright suite passes in CI.

## 4. Order of work and dependencies

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 4
                          │                     │
                          └──────► Phase 5 ─► Phase 6 ─► Phase 7
```

Phases 4 and 5 can run in parallel once Phase 3 is done. Total: about 9 to 10 weeks for one person; about 6 with two (one frontend, one backend/AI).

## 5. Risks and decisions to confirm

| Risk / decision | Suggested handling |
| --- | --- |
| gpt-oss 20b output is inconsistent (invalid JSON, wrong answers in quizzes) | Pydantic validation, repair retry, a validation node, human review before publish |
| Tailscale Ollama is a single point of failure and slow | Async jobs, queue with retries, fake provider for dev/CI, clear "generating" UI state |
| Scanned or handwritten input quality | Show extracted text to faculty for correction before the syllabus graph runs |
| Vue → React rewrite duplicates UI work | Keep `style.css` tokens as the single source; port screen by screen against the checklist |
| "Level" model is richer than the prototype (which uses mastery %) | Decide in Phase 3: levels derived from mastery thresholds (simplest) vs. stored independently |
| Tailwind vs. the prototype's hand-written CSS | Tailwind with the prototype tokens mapped into `tailwind.config`; no visual redesign |
| Scope creep (registration, password reset, notifications) | Out of scope until Phase 7; track as a backlog |

## 6. Proposed repo layout

```
gradient/
  prototype/            reference, kept until Phase 7
  backend/
    app/{api,services,repos,agents,models,core}/
    alembic/  tests/  seed/
  frontend/
    app/  components/  lib/api-client/  styles/
  infra/                docker-compose, Dockerfiles, env examples
  ARCHITECTURE.md
```
