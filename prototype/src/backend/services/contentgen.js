// Stand-in for the content-generation agent. It builds study material for
// faculty-created courses from each sub-topic's key points. A real deployment
// would call an LLM here; the shape of the output is what the app relies on.
import { shuffle } from '../util.js'

const FILLERS = [
  'It is outside the scope of this course',
  'It applies only to unrelated subjects',
  'It is covered only in advanced postgraduate courses',
]

const splitPoint = (point) => {
  const m = point.match(/^(.{3,60}?)\s*(?::|—|–|\s-\s)\s*(.+)$/)
  return m ? { term: m[1].trim(), detail: m[2].trim() } : null
}

export function generateSubContent(sub, course) {
  const points = (sub.points || []).filter(Boolean)
  const title = sub.title
  const others = course.topics.flatMap((t) => t.subtopics).filter((s) => s.id !== sub.id).flatMap((s) => s.points || [])

  const cards = points.map((p, i) => {
    const sp = splitPoint(p)
    return sp
      ? { front: `What is meant by “${sp.term}” in ${title}?`, back: sp.detail }
      : { front: `Key idea ${i + 1} of “${title}”`, back: p }
  })

  const questions = points.slice(0, 4).map((p, i) => {
    const pool = shuffle(others.filter((o) => o !== p))
    const wrong = [...pool.slice(0, 3)]
    for (const f of FILLERS) if (wrong.length < 3) wrong.push(f)
    return {
      id: `${sub.id}-q${i + 1}`,
      text: `Which of the following is a key idea in “${title}”?`,
      options: [p, ...wrong],
      answer: 0,
      explanation: `“${p}” is listed as a key idea for ${title}.`,
    }
  })

  return {
    flashcards: cards,
    questions,
    remediation: {
      explanation: `Go back to the basics of ${title}. ${sub.description || ''}`.trim(),
      steps: [
        `Re-read the summary for ${title}.`,
        'Write each key idea in your own words without looking.',
        points[0] ? `Explain “${points[0]}” to a classmate or in a short paragraph.` : 'Explain the topic to a classmate.',
      ],
    },
  }
}

export function defaultSummary(sub, topic) {
  const pts = (sub.points || []).filter(Boolean)
  return [
    `${sub.title} is part of ${topic.title}. ${sub.description || ''}`.trim(),
    pts.length ? `Key ideas: ${pts.join('; ')}.` : 'Key ideas will be added by the course team.',
  ]
}

/** Regenerate flashcards, questions and remediation for sub-topics flagged as generated. */
export function refreshGenerated(course) {
  for (const topic of course.topics) {
    for (const sub of topic.subtopics) {
      if (!sub.generated) continue
      Object.assign(sub, generateSubContent(sub, course))
      if (!sub.summary || !sub.summary.some((p) => p && p.trim())) sub.summary = defaultSummary(sub, topic)
    }
  }
  return course
}
