const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const parse = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}
const todayISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export const fmtDate = (iso) => {
  if (!iso) return '—'
  const d = parse(iso)
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
}
export const fmtDay = (iso) => {
  if (!iso) return '—'
  const d = parse(iso)
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`
}
export const fmtTs = (ts) => {
  const d = new Date(ts)
  return `${d.getDate()} ${MONTHS[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
export const relDay = (iso) => {
  if (!iso) return '—'
  const diff = Math.round((parse(iso) - parse(todayISO())) / 864e5)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  if (diff === -1) return 'Yesterday'
  return fmtDay(iso)
}
export const isToday = (iso) => iso === todayISO()
export const plural = (n, w, pl = w + 's') => `${n} ${n === 1 ? w : pl}`
export const firstName = (name) => name.replace(/^(Dr|Prof)\.?\s+/, '').split(' ')[0]

export const TASK_LABEL = {
  study: 'Study',
  quiz: 'Quiz',
  confirm: 'Confirmation quiz',
  remediation: 'Remediation',
  retake: 'Retake',
  'topic-quiz': 'Topic quiz',
}
export const STATUS_LABEL = { new: 'Not started', learning: 'In progress', review: 'Needs review', mastered: 'Mastered' }
export const ENR_STATUS = { 'on-track': 'On track', attention: 'Needs attention', completed: 'Completed' }

/** Route for opening a plan task. */
export const taskRoute = (courseId, t) => {
  const base = `/student/courses/${courseId}`
  if (t.type === 'study') return { path: `${base}/subtopics/${t.subtopicId}`, query: { tab: 'summary' } }
  if (t.type === 'remediation') return { path: `${base}/subtopics/${t.subtopicId}`, query: { tab: 'help' } }
  if (t.type === 'topic-quiz') return { path: `${base}/quiz`, query: { kind: 'topic', topicId: t.topicId } }
  return { path: `${base}/quiz`, query: { kind: 'subtopic', subtopicId: t.subtopicId } }
}
