// Builders that keep the course data files compact.
// The correct option is always written first; the quiz service shuffles at runtime.

/** Question: text, correct answer, three distractors, explanation. */
export const q = (text, right, wrong, explanation) => ({
  text,
  options: [right, ...wrong],
  answer: 0,
  explanation,
})

/** Flashcard */
export const fc = (front, back) => ({ front, back })

/** Sub-topic with summary, flashcards, questions and remediation material. */
export const sub = (id, title, description, c) => ({
  id,
  title,
  description,
  points: c.points,
  summary: c.summary,
  flashcards: c.cards,
  questions: c.questions.map((x, i) => ({ id: `${id}-q${i + 1}`, ...x })),
  remediation: c.remediation,
})
