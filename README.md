# Gradient

An AI tutor that turns a syllabus or course notes into a personal study path for each learner.

## What it does

- Faculty upload a syllabus. The system breaks it into topics and sub-topics.
- A student picks a course and takes a short pre-test.
- The system builds a study plan from the results.
- Each sub-topic comes with a summary, flashcards and a quiz, all matched to the student's current level.
- Levels run Beginner, Intermediate, Advanced, Expert. A good quiz score moves the student up. A low score keeps them at the level and adds extra material.
- Every quiz attempt is saved, so students can see their history and progress.
- Admins set the passing threshold and see every student's progress.

## Roles

| Role    | Can do                                  |
| ------- | --------------------------------------- |
| Student | Study, take quizzes, track progress     |
| Faculty | Upload syllabus, review and edit topics |
| Admin   | Set thresholds, view all progress       |

## Tech stack

- Frontend: Next.js, React, Tailwind CSS
- Backend: FastAPI (Python), JWT auth
- AI: LangGraph with gpt-oss 120B via Ollama, Gemma for scanned or handwritten input
- Data: PostgreSQL, Redis, ChromaDB
- Runs in Docker
