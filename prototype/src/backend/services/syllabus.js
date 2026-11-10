// Syllabus analysis "agent": turns an uploaded syllabus into topics, then
// derives sub-topics for the topics a faculty member chooses to keep.
// It is rule-based so the prototype works offline; the returned `trace`
// mimics the steps an LLM agent would report.
import { db, save, clock } from '../db.js'
import { ApiError, uid } from '../util.js'
import { refreshGenerated } from './contentgen.js'

const HEADING = /^(?:#{1,2}\s+|(?:unit|module|week|chapter|topic|part|section)\s*\d+\s*[:.\-–—]?\s*)(.+)$/i
const NUMBERED = /^\d+[.)]\s+(.+)$/
const BULLET = /^(?:[-*•–]\s+|\d+\.\d+[.)]?\s+|[a-z][.)]\s+)(.+)$/

const clean = (s) => s.replace(/[*_`#]/g, '').replace(/\s+/g, ' ').trim().replace(/[.;:,]+$/, '')
const titleCase = (s) => (s === s.toUpperCase() ? s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) : s)

export const SAMPLE_SYLLABUS = `Introduction to Data Structures — Course Outline

Unit 1: Linear Structures
- Arrays and dynamic arrays: contiguous storage, resizing, amortised cost
- Linked lists: singly linked, doubly linked, insertion and deletion
- Stacks and queues: LIFO, FIFO, applications

Unit 2: Trees
- Binary trees: terminology, traversals
- Binary search trees: search, insert, delete, balance
- Heaps and priority queues

Unit 3: Graphs
- Graph representations: adjacency list, adjacency matrix
- Breadth-first and depth-first search
- Shortest paths

Unit 4: Hashing
- Hash functions and collisions
- Open addressing and chaining
`

/** Parse raw syllabus text into [{title, subs[], note}] */
export function parseOutline(text) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  const headings = lines.filter((l) => HEADING.test(l)).length
  const strong = headings >= 2
  const topics = []
  let cur = null
  const startTopic = (title) => {
    cur = { title: titleCase(clean(title)), subs: [], note: '' }
    topics.push(cur)
  }
  for (const line of lines) {
    const h = line.match(HEADING)
    const n = line.match(NUMBERED)
    const b = line.match(BULLET)
    if (h && (strong || !n)) {
      startTopic(h[1])
    } else if (!strong && n && !b) {
      startTopic(n[1])
    } else if (b || (strong && n)) {
      if (!cur) startTopic('Introduction')
      cur.subs.push(clean((b || n)[1]))
    } else if (cur) {
      cur.note = cur.note ? `${cur.note} ${clean(line)}` : clean(line)
    }
  }
  const tl = topics.find((t) => t.title.includes(':')) // "Topic: a, b, c"
  if (tl || topics.some((t) => !t.subs.length)) {
    for (const t of topics) {
      const m = t.title.match(/^(.{3,50}?):\s*(.+,.+)$/)
      if (m && !t.subs.length) {
        t.title = m[1]
        t.subs = m[2].split(/,|;/).map(clean).filter(Boolean)
      }
    }
  }
  return topics.filter((t) => t.title)
}

const templateOutline = (name) => [
  { title: `Foundations of ${name}`, subs: [], note: '' },
  { title: `Core Concepts in ${name}`, subs: [], note: '' },
  { title: `Applying ${name}`, subs: [], note: '' },
  { title: 'Assessment and Review', subs: [], note: '' },
]

/** Step 1 + 2: read the upload and propose topics. */
export function analyze({ fileName, text, courseTitle }) {
  if (!fileName && !text) throw new ApiError('Upload a syllabus file or paste its text.')
  const trace = [{ step: 'Reading the document', detail: fileName || 'Pasted text' }]
  let topics = []
  let simulated = false
  const body = (text || '').trim()
  if (body) {
    trace.push({ step: 'Detecting structure', detail: `${body.split(/\r?\n/).filter(Boolean).length} non-empty lines scanned for headings and lists` })
    topics = parseOutline(body)
  }
  if (!topics.length) {
    simulated = true
    const name = courseTitle || (fileName ? fileName.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ') : 'the subject')
    trace.push({ step: 'Extracting text', detail: 'Scanned or binary file: the prototype uses a template outline here. The full system runs a parsing / OCR service for this step.' })
    topics = templateOutline(name)
  }
  trace.push({ step: 'Grouping into topics', detail: `${topics.length} candidate topics found` })

  const draftId = uid('draft')
  const out = topics.map((t, i) => ({
    id: `dt${i + 1}`,
    title: t.title,
    note: t.note,
    subs: t.subs,
    confidence: t.subs.length >= 2 ? 'high' : t.subs.length === 1 ? 'medium' : 'low',
    selected: true,
  }))
  db().drafts[draftId] = { id: draftId, fileName: fileName || null, topics: out, createdAt: clock.now() }
  save()
  return { draftId, fileName: fileName || null, simulated, trace, topics: out }
}

const splitSub = (line) => {
  const m = line.match(/^(.{3,70}?)\s*(?::|—|–|\s-\s)\s*(.+)$/)
  if (!m) return { title: line.slice(0, 80), points: [] }
  const detail = m[2].split(/,|;/).map(clean).filter(Boolean)
  return { title: m[1].trim(), points: detail }
}

const inferSubs = (title) => {
  const parts = title.split(/,|\band\b|&/i).map((s) => s.trim()).filter((s) => s.length > 2)
  if (parts.length >= 2) return parts.slice(0, 4).map((p) => ({ title: p.replace(/^\w/, (c) => c.toUpperCase()), points: [] }))
  return [
    { title: `Foundations of ${title}`, points: [] },
    { title: `Key concepts in ${title}`, points: [] },
    { title: `Applying ${title}`, points: [] },
  ]
}

/** Step 3: derive sub-topics for the selected topics and create a draft course. */
export function derive(user, { draftId, selectedIds, meta }) {
  const draft = db().drafts[draftId]
  if (!draft) throw new ApiError('That upload could not be found. Please upload it again.', 404)
  const chosen = draft.topics.filter((t) => selectedIds.includes(t.id))
  if (!chosen.length) throw new ApiError('Select at least one topic to continue.')
  if (!meta?.title?.trim() || !meta?.code?.trim()) throw new ApiError('Course code and title are required.')

  const topics = chosen.map((t, ti) => {
    const subs = (t.subs.length ? t.subs.map(splitSub) : inferSubs(t.title)).map((s, si) => {
      const id = `g${draftId.slice(-6)}-${ti + 1}-${si + 1}`
      const points = s.points.length
        ? s.points
        : [`Core definitions and terminology of ${s.title}`, `Typical problems that use ${s.title}`, `Common mistakes when working with ${s.title}`]
      return {
        id,
        title: s.title,
        description: t.note || `Derived from the syllabus topic “${t.title}”.`,
        points,
        summary: [],
        flashcards: [],
        questions: [],
        remediation: { explanation: '', steps: [] },
        generated: true,
      }
    })
    return { id: `t${draftId.slice(-6)}-${ti + 1}`, title: t.title, subtopics: subs }
  })

  const course = refreshGenerated({
    id: uid('course'),
    code: meta.code.trim(),
    title: meta.title.trim(),
    department: meta.department?.trim() || user.department || 'General',
    credits: Number(meta.credits) || 3,
    level: meta.level?.trim() || 'Undergraduate',
    accent: '#3d4f7a',
    description: meta.description?.trim() || `Course derived from ${draft.fileName || 'the uploaded syllabus'}.`,
    instructorId: user.id,
    status: 'draft',
    source: { fileName: draft.fileName },
    topics,
  })
  db().courses.push(course)
  delete db().drafts[draftId]
  save()
  return { courseId: course.id, topics: topics.length, subtopics: topics.reduce((n, t) => n + t.subtopics.length, 0) }
}
