# Acceptance scenarios

Extracted from the prototype's demo data (`prototype/README.md`). Every phase is accepted against these.
Status: ✅ passing · ⏳ not yet built. Accounts are seeded by `python -m app.seed.run`.

## Authentication and routing (Phases 0–1)

| # | Scenario | Status |
| - | -------- | ------ |
| A1 | `meera.iyer@gradient.edu` / `student123` on the Student portal lands on `/student` | ✅ |
| A2 | `fatima.khan@gradient.edu` / `student123` lands on `/student` | ✅ |
| A3 | `ananya.rao@gradient.edu` / `faculty123` on the Faculty / Management portal lands on `/faculty` | ✅ |
| A4 | `richard.hale@gradient.edu` / `admin123` on the Faculty / Management portal lands on `/admin` | ✅ |
| A5 | A student account on the staff portal (and the reverse) is refused with the portal message, no session created | ✅ |
| A6 | Wrong password and unknown email give the same 401 message | ✅ |
| A7 | Visiting another role's area redirects to the user's own home; API routes return 403 | ✅ |
| A8 | Signed-out visit to a protected page goes to `/login?redirect=…`; sign-in returns there (own area only) | ✅ |
| A9 | Expired access token with a valid refresh token continues silently; after sign-out nothing is accessible | ✅ |

## Browsing (Phase 2)

| # | Scenario | Status |
| - | -------- | ------ |
| B1 | Student catalog lists the three published courses (CS 101, CS 201, ECON 101) with counts and instructor | ✅ |
| B2 | Course page lists topics and sub-topics; drafts and unknown ids are 404 | ✅ |
| B3 | Sub-topic page shows summary, key points, flashcards and extra help; prev/next navigation works | ✅ |
| B4 | Students never receive quiz answers; faculty see only their own courses, management sees all | ✅ |

## Study flow (Phase 3)

| # | Scenario | Status |
| - | -------- | ------ |
| S1 | Meera sees C with a plan partway through, one failed quiz, and its reschedule + remediation task | ✅ |
| S2 | Fatima enrols in a course, sits the pre-test, and receives a plan (known sub-topics get a short confirmation quiz, weakest first) | ✅ |
| S3 | Failing a sub-topic quiz (below pass mark) flags review, adds remediation and a retake, and repacks later days within the daily budget | ✅ |
| S4 | Passing sets mastery to at least the score and promotes the level; failing moves mastery halfway to the score and keeps the level | ✅ |
| S5 | Unfinished tasks from earlier days roll forward to today | ✅ |
| S6 | End-of-day status reads e.g. "Day 3 completed – 100% mastery" | ✅ |
| S7 | "Quiz me on…" on-demand quiz works for any sub-topic | ✅ |

S1–S7 are covered by `backend/tests/test_learning.py` and, end to end in a real browser, by
`frontend/e2e/student-journey.spec.ts`.

## Staff flows (Phases 4–6)

M1 and M2 are covered by `backend/tests/test_admin.py` and `frontend/e2e/admin-journey.spec.ts`.

| # | Scenario | Status |
| - | -------- | ------ |
| M1 | Management sets a global pass mark and a per-course override; new attempts use it (even a quiz already open) | ✅ |
| M2 | Management dashboard lists every student with overall %, per-topic mastery, upcoming tasks; search, course and status filters, pagination, and a read-only detail page | ✅ |
| F1 | Faculty uploads or pastes a syllabus, selects topics, reviews derived sub-topics, edits, and publishes | ✅ (e2e-faculty) |
| F2 | A published faculty course appears in the student catalog | ✅ (API tests) |
