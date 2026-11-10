# Gradient — Prototype

A working front-end prototype of **Gradient**, an adaptive learning portal for university courses. Faculty upload a syllabus, students take a pre-test and receive a personalised study plan, and the plan reschedules itself when a quiz comes back below the pass mark. Management sees every student's progress and sets the pass mark.

There is no server. A JavaScript "backend" in `src/backend/` stands in for the real API, and its data is stored in the browser's `localStorage`, so changes survive a refresh. The real system (FastAPI, LangGraph, PostgreSQL) is described in the repository's top-level [README](../README.md).

Built with Vue 3, Vite and vue-router. App code is plain JS and Vue single-file components; TypeScript is used for the build configuration and type-checking.

## Run it

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check and production build
```

### Demo accounts

| Portal               | Account                                  | Password     | What you see                                               |
| -------------------- | ---------------------------------------- | ------------ | ---------------------------------------------------------- |
| Student              | `meera.iyer@gradient.edu`                | `student123` | Mid-way through a plan, with one failed quiz and its reschedule |
| Student              | `fatima.khan@gradient.edu`               | `student123` | New student: enrol in a course and sit the pre-test        |
| Faculty / Management | `ananya.rao@gradient.edu` (Faculty)      | `faculty123` | Syllabus upload and topic editor                           |
| Faculty / Management | `richard.hale@gradient.edu` (Management) | `admin123`   | Progress dashboard and pass mark settings                  |

The other seeded students also use `student123`. **Reset demo data** on the login page restores the original data.

## Features implemented

Against the MVP checklist:

**Login**
- [x] Student login
- [x] Faculty / Management login (one portal; the account's role decides the landing page)

**Faculty**
- [x] Syllabus upload page (file or pasted text, with a sample syllabus)
- [x] Topic selection after upload
- [x] Agent that derives sub-topics from the upload
- [x] Left sidebar to review and edit topics and sub-topics (rename, add, remove, reorder, edit key points and summary, save, publish)

**Admin (Management)**
- [x] Quiz passing threshold, global or per course
- [x] Dashboard with every student's progress: overall %, per-topic mastery and upcoming tasks, with filters and a per-student detail page

**Student**
- [x] Course picker (C, C++ and Microeconomics are seeded; faculty-uploaded courses appear once published)
- [x] Topics and sub-topics listed for the chosen course
- [x] Pre-test before the plan is created
- [x] Personalised study plan from pre-test results
- [x] Summary for each sub-topic
- [x] Flashcards for each sub-topic
- [x] Quiz after each sub-topic and each topic
- [x] On-demand quiz ("Quiz me on…" search)
- [x] End-of-day status, e.g. "Day 3 completed – 100% mastery"
- [x] Progress dashboard

**Adaptive logic**
- [x] A score below the threshold reschedules the topic for a later day
- [x] Remediation material is added to the plan
- [x] The rest of the plan is recalculated (also when the daily study time changes or tasks are missed)

**UI**
- [x] Redesigned as a modern editorial university portal in place of the dark notebook prototype: ink and crimson on warm ivory, flat colour with no gradients, Spectral serif headings with Public Sans for the interface, a deep oxblood hero on the student dashboard, a mastery-curve motif (logo, login and dashboard), a simple text navigation, and short eased motion for page entrances, rings, meters and flashcard flips. Motion is switched off under `prefers-reduced-motion`, and the layout is designed separately for phone widths
- [x] Login screens are part of the main design
- [x] Progress dashboard views for admin and student (both use one shared component)

### How the adaptive logic works

- Initial mastery for each sub-topic is half its pre-test score.
- Sub-topics the student already knows (pre-test score at or above the pass mark) only get a short confirmation quiz. The others get a study task and a quiz, weakest first. Each topic ends with a topic quiz.
- Mastery only moves on evidence. A passing score sets it to at least that score; a failing score moves it halfway toward the score.
- A quiz below the pass mark flags the sub-topic for review, adds a remediation task and a retake a few tasks later, then repacks all unfinished tasks into days within the daily time budget.
- Unfinished tasks from earlier days roll forward to today the next time the plan is opened.

## Project structure

```
src/
  main.ts, App.vue          App bootstrap
  style.css                 Design tokens and shared styles
  router/index.js           Routes and the role-based navigation guard
  stores/                   session.js (signed-in user), toast.js
  lib/                      format.js (dates, labels, task links), useAsync.js (data loading)
  components/               Shared UI (see below)
  views/                    One file per screen, grouped by role
  backend/                  The mock backend (see below)
```

### Backend modules (`src/backend/`)

| Module | Description |
| ------ | ----------- |
| `index.js` | The API the UI calls (`api.auth`, `api.student`, `api.faculty`, `api.admin`). Every call is async with simulated latency, checks the session and role, and returns plain JSON. |
| `db.js` | Document store backed by `localStorage` (key `gradient.db.v2`; bump the version to force a reseed after changing seed data), plus a clock the seed script can shift. |
| `seed.js` | Builds the demo data by driving the real services with the clock moved back, so seeded students have genuine history. |
| `data/users.js` | Demo accounts and the list shown on the login page. |
| `data/course-*.js`, `data/helpers.js` | The three seeded courses: topics, sub-topics, summaries, flashcards, quiz questions and remediation. `helpers.js` holds the small builders used to write them compactly. |
| `hash.js` | Non-cryptographic password hash used for the demo. |
| `services/auth.js` | Login by portal, sessions via a token in `localStorage`, role checks. |
| `services/courses.js` | Course listing, editing, publish and unpublish for staff; read-only structure for students. |
| `services/syllabus.js` | The syllabus agent: parses headings and bullets into topics, then derives sub-topics for the selected ones. |
| `services/contentgen.js` | Generates flashcards, questions and remediation for faculty-created courses from their key points. |
| `services/planner.js` | Pure functions that build a plan from pre-test results, pack tasks into days, and insert follow-up tasks. |
| `services/learning.js` | Enrolment, pre-test, quizzes, grading, mastery updates, the adaptive rules and end-of-day status. |
| `services/metrics.js` | Read-only aggregates for the student and admin dashboards. |
| `services/settings.js` | Global and per-course pass marks. |

### UI modules

| Area | Files |
| ---- | ----- |
| Shell | `AppShell.vue` (header, role-based navigation, sign out), `ToastHost.vue`, `PageHeader.vue`, `LoadState.vue`, `Crest.vue` |
| Display | `RingProgress.vue`, `MeterBar.vue` (with pass-mark marker), `TaskRow.vue`, `Icon.vue` (the single stroke-icon set) |
| Learning | `QuizSession.vue` (intro, questions and results; used for the pre-test and every quiz), `QuizRunner.vue`, `FlashcardDeck.vue`, `EnrollmentProgress.vue` |
| Login | `views/LoginView.vue` |
| Student | `StudentDashboard`, `CourseCatalog`, `CourseView`, `QuizView` (pre-test and quizzes), `PlanView`, `SubtopicView`, `PracticeView`, `ProgressView` |
| Faculty | `FacultyCourses`, `SyllabusUpload`, `CourseEditor` |
| Management | `AdminDashboard`, `StudentDetail`, `AdminSettings` |

## Design system

All styling lives in `src/style.css`; there is no CSS framework. Change the look by editing the tokens at the top of the file.

| Token | Purpose |
| ----- | ------- |
| `--gold` (`#8e2433`, crimson) | The single accent: active navigation, eyebrows, primary highlight buttons, step and tab indicators. The name is historical. |
| `--navy` and `--navy-700/100/50` | Warm ink: headings, primary buttons, and the neutral tints behind them. The names are historical. |
| `--deep` | Oxblood background for the dashboard hero, login panel and flashcard backs. |
| `--paper`, `--surface`, `--line` | Page background, cards, hairlines. |
| `--ok`, `--warn`, `--bad` | Status colours, used only to carry meaning (passed, close, below pass mark). |
| `--serif`, `--sans` | Spectral for headings, Public Sans for the interface. Both load from Google Fonts in `index.html`, so a network connection is needed for the intended typography; system fonts are the fallback. |

Principles: flat colour, hairlines before shadows, one accent, small corners (6–8px), and motion only where it shows state or order (page entrances, rings and meters filling, task ticks, flashcard flips). Course cards take their colour from the course's `accent` field. Icons come from one component, `Icon.vue`.

## Limits of the prototype

- **Auth is a demonstration.** Passwords are hashed with a trivial function and sessions are a token in `localStorage`. Do not reuse it for anything real.
- **The agent is rule-based.** It reads `.txt`, `.md` and pasted text. PDF and Word files cannot be parsed in the browser, so those uploads get a template outline; the real system parses and OCRs them.
- **Generated study material is templated.** Flashcards and questions for faculty-created courses are built from key points, not by a language model. The three seeded courses have hand-written content.
- **Data is per browser.** Clearing site data, or using Reset demo data, restores the seed.
- Not included: registration, password reset, notifications, and editing of individual quiz questions.
