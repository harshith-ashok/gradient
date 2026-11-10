// Student-facing learning engine: enrolment, pre-test, personalised plan,
// quizzes, and the adaptive rules that react to a low score.
import { db, save, clock } from '../db.js'
import { ApiError, uid, shuffle, avg, dayDiff } from '../util.js'
import { findCourse, allSubtopics, structure } from './courses.js'
import { thresholdFor } from './settings.js'
import { buildTasks, repack, insertLater, makeTask, MINUTES, QUIZ_LIKE } from './planner.js'
import { enrollmentSummary, enrollmentDetail, subStatus } from './metrics.js'

const sessions = new Map() // quiz sessions are short-lived, so they live in memory
const DEFAULT_MINUTES = 60
export const MINUTES_OPTIONS = [30, 45, 60, 90, 120]

const myEnrollment = (user, courseId) => db().enrollments.find((e) => e.userId === user.id && e.courseId === courseId)
function mustEnrollment(user, courseId) {
  const enr = myEnrollment(user, courseId)
  if (!enr) throw new ApiError('You are not enrolled in this course yet.', 404)
  refresh(enr)
  return enr
}
const addNotice = (enr, kind, text) => enr.plan.notices.push({ id: uid('n'), ts: clock.now(), kind, text })
const finish = (t, result) => {
  t.done = true
  t.doneAt = clock.now()
  t.result = result
}
const freshMastery = (value = 0) => ({ value, lastScore: null, attempts: 0, studied: false, remediation: false })

/** Keep an enrolment consistent with the course and the calendar. */
function refresh(enr) {
  const course = findCourse(enr.courseId)
  const subIds = new Set(allSubtopics(course).map((x) => x.sub.id))
  const topicIds = new Set(course.topics.map((t) => t.id))
  const before = enr.plan.tasks.length
  enr.plan.tasks = enr.plan.tasks.filter((t) => t.done || (topicIds.has(t.topicId) && (t.subtopicId == null || subIds.has(t.subtopicId))))
  const removed = before - enr.plan.tasks.length
  for (const id of subIds) if (!enr.mastery[id]) enr.mastery[id] = freshMastery()
  const todayIdx = Math.max(0, dayDiff(enr.plan.startDate, clock.todayISO()))
  const overdue = enr.plan.tasks.filter((t) => !t.done && t.day < todayIdx).length
  if (overdue || removed) {
    repack(enr.plan.tasks, enr.plan.startDate, clock.todayISO(), enr.plan.minutesPerDay)
    if (overdue) addNotice(enr, 'recalc', `${overdue} unfinished ${overdue === 1 ? 'task' : 'tasks'} from earlier days moved forward and the rest of the plan was recalculated.`)
    if (removed) addNotice(enr, 'recalc', 'The course outline changed, so your plan was updated.')
    save()
  }
}

/** Day status: when every task of a day is done, record "Day N completed – X% mastery". */
function checkDays(enr, course, days) {
  const created = []
  for (const d of [...days].sort((a, b) => a - b)) {
    const todays = enr.plan.tasks.filter((t) => t.day === d)
    if (!todays.length || todays.some((t) => !t.done)) continue
    if (enr.dayStatuses.some((s) => s.dayIndex === d)) continue
    const subIds = new Set()
    for (const t of todays) {
      if (t.subtopicId) subIds.add(t.subtopicId)
      else course.topics.find((x) => x.id === t.topicId)?.subtopics.forEach((s) => subIds.add(s.id))
    }
    const mastery = avg([...subIds].map((id) => enr.mastery[id]?.value ?? 0))
    const status = {
      id: uid('ds'),
      dayIndex: d,
      day: d + 1,
      date: todays[0].date,
      mastery,
      message: `Day ${d + 1} completed – ${mastery}% mastery`,
      ts: clock.now(),
    }
    enr.dayStatuses.push(status)
    created.push(status)
  }
  return created[created.length - 1] || null
}

/* ---------- Quizzes ---------- */

function pickQuestions(sub, n) {
  return shuffle(sub.questions)
    .slice(0, n)
    .map((q) => {
      const opts = shuffle(q.options.map((text, i) => ({ text, ok: i === q.answer })))
      return { id: q.id, subtopicId: sub.id, text: q.text, options: opts.map((o) => o.text), answer: opts.findIndex((o) => o.ok), explanation: q.explanation }
    })
}

export function startQuiz(user, { courseId, kind, topicId, subtopicId }) {
  const course = findCourse(courseId)
  if (!course || course.status !== 'published') throw new ApiError('Course not found.', 404)
  const enr = myEnrollment(user, courseId)
  let questions = []
  let title = ''
  let scope = ''
  if (kind === 'pretest') {
    if (enr) throw new ApiError('You have already taken the pre-test for this course.')
    questions = allSubtopics(course).flatMap(({ sub }) => pickQuestions(sub, 2))
    title = `Pre-test: ${course.title}`
    scope = 'Diagnostic across every sub-topic'
  } else {
    if (!enr) throw new ApiError('Enrol in this course first.', 404)
    if (kind === 'topic') {
      const topic = course.topics.find((t) => t.id === topicId)
      if (!topic) throw new ApiError('Topic not found.', 404)
      questions = topic.subtopics.flatMap((s) => pickQuestions(s, 2))
      title = `Topic quiz: ${topic.title}`
      scope = `${topic.subtopics.length} sub-topics`
    } else {
      const hit = allSubtopics(course).find((x) => x.sub.id === subtopicId)
      if (!hit) throw new ApiError('Sub-topic not found.', 404)
      questions = pickQuestions(hit.sub, 4)
      title = `${kind === 'ondemand' ? 'Practice quiz' : 'Quiz'}: ${hit.sub.title}`
      scope = hit.topic.title
    }
  }
  if (!questions.length) throw new ApiError('No questions are available for this selection yet.')
  const id = uid('quiz')
  sessions.set(id, { id, userId: user.id, courseId, kind, topicId, subtopicId, title, scope, questions })
  return {
    quizId: id,
    kind,
    courseId,
    title,
    scope,
    threshold: kind === 'pretest' ? null : thresholdFor(courseId),
    questions: questions.map((q) => ({ id: q.id, text: q.text, options: q.options })),
  }
}

/** Seed/test helper: reveal the answer key of an open quiz session. */
export const peekAnswerKey = (quizId) => Object.fromEntries(sessions.get(quizId).questions.map((q) => [q.id, q.answer]))

export function submitQuiz(user, quizId, answers) {
  const sess = sessions.get(quizId)
  if (!sess || sess.userId !== user.id) throw new ApiError('This quiz session has expired. Please start it again.', 410)
  sessions.delete(quizId)
  const course = findCourse(sess.courseId)
  const thr = thresholdFor(course.id)
  const subTitle = (id) => allSubtopics(course).find((x) => x.sub.id === id)?.sub.title || ''

  const graded = sess.questions.map((q) => {
    const chosen = Number.isInteger(answers[q.id]) ? answers[q.id] : null
    return { ...q, chosen, correct: chosen === q.answer, subtopicTitle: subTitle(q.subtopicId) }
  })
  const per = {}
  for (const g of graded) {
    per[g.subtopicId] ||= { correct: 0, total: 0 }
    per[g.subtopicId].total++
    if (g.correct) per[g.subtopicId].correct++
  }
  for (const v of Object.values(per)) v.score = Math.round((100 * v.correct) / v.total)
  const correct = graded.filter((g) => g.correct).length
  const score = Math.round((100 * correct) / graded.length)
  const review = graded.map((g) => ({ id: g.id, text: g.text, options: g.options, chosen: g.chosen, answer: g.answer, correct: g.correct, explanation: g.explanation, subtopicTitle: g.subtopicTitle }))

  return sess.kind === 'pretest'
    ? finishPretest(user, sess, course, per, score, correct, graded.length, review, subTitle)
    : finishQuiz(user, sess, course, thr, per, score, correct, graded.length, review, subTitle)
}

function finishPretest(user, sess, course, per, score, correct, total, review, subTitle) {
  const thr = thresholdFor(course.id)
  const today = clock.todayISO()
  const mastery = {}
  for (const { sub } of allSubtopics(course)) mastery[sub.id] = freshMastery(Math.round((per[sub.id]?.score ?? 0) * 0.5))
  const tasks = buildTasks(course, per, thr)
  repack(tasks, today, today, DEFAULT_MINUTES)
  const known = Object.values(per).filter((p) => p.score >= thr).length
  const enr = {
    id: uid('enr'),
    userId: user.id,
    courseId: course.id,
    createdAt: clock.now(),
    pretest: { takenAt: clock.now(), score, bySubtopic: per },
    mastery,
    plan: { startDate: today, minutesPerDay: DEFAULT_MINUTES, tasks, notices: [] },
    dayStatuses: [],
  }
  addNotice(enr, 'info', `Plan created from your pre-test: ${Object.keys(per).length - known} ${Object.keys(per).length - known === 1 ? 'sub-topic needs' : 'sub-topics need'} full study and ${known} ${known === 1 ? 'needs' : 'need'} only a quick confirmation quiz.`)
  db().enrollments.push(enr)
  db().attempts.push({ id: uid('att'), enrollmentId: enr.id, userId: user.id, courseId: course.id, kind: 'pretest', title: sess.title, score, correct, total, passed: null, threshold: null, ts: clock.now(), subtopicIds: Object.keys(per) })
  save()
  return {
    kind: 'pretest',
    courseId: course.id,
    score,
    correct,
    total,
    passed: null,
    threshold: thr,
    review,
    bySubtopic: Object.entries(per).map(([id, p]) => ({ subtopicId: id, title: subTitle(id), score: p.score, correct: p.correct, total: p.total, after: mastery[id].value })),
    plan: { days: new Set(tasks.map((t) => t.day)).size, tasks: tasks.length, minutesPerDay: DEFAULT_MINUTES },
  }
}

function finishQuiz(user, sess, course, thr, per, score, correct, total, review, subTitle) {
  const enr = mustEnrollment(user, course.id)
  const passed = score >= thr
  const tasks = enr.plan.tasks
  const touchedDays = new Set()
  const done = (t, r) => {
    finish(t, r)
    touchedDays.add(t.day)
  }

  // 1. update mastery
  const bySubtopic = []
  for (const [sid, p] of Object.entries(per)) {
    const rec = enr.mastery[sid] || (enr.mastery[sid] = freshMastery())
    const before = rec.value
    rec.attempts++
    rec.studied = true
    rec.lastScore = p.score
    rec.value = p.score >= thr ? Math.max(before, p.score) : Math.max(before, Math.round((before + p.score) / 2))
    if (p.score >= thr) rec.remediation = false
    bySubtopic.push({ subtopicId: sid, title: subTitle(sid), score: p.score, correct: p.correct, total: p.total, before, after: rec.value })
  }

  const result = `${score}%`
  const actions = { failed: !passed, items: [], shifted: 0 }
  const isTopic = sess.kind === 'topic'
  const topicOf = (sid) => course.topics.find((t) => t.subtopics.some((s) => s.id === sid))

  if (passed) {
    if (isTopic) {
      tasks.filter((t) => !t.done && t.type === 'topic-quiz' && t.topicId === sess.topicId).forEach((t) => done(t, result))
    } else {
      tasks.filter((t) => !t.done && QUIZ_LIKE.includes(t.type) && t.subtopicId === sess.subtopicId).forEach((t) => done(t, result))
      for (let i = tasks.length - 1; i >= 0; i--) if (!tasks[i].done && tasks[i].type === 'remediation' && tasks[i].subtopicId === sess.subtopicId) tasks.splice(i, 1)
    }
    if (!tasks.some((t) => !t.done)) addNotice(enr, 'info', 'Every task in your plan is complete.')
  } else {
    // 2. adaptive logic: reschedule, add remediation, recalculate
    let failing = isTopic ? bySubtopic.filter((b) => b.score < thr) : bySubtopic
    if (!failing.length) failing = [bySubtopic.slice().sort((a, b) => a.score - b.score)[0]]
    const failingIds = new Set(failing.map((f) => f.subtopicId))
    failingIds.forEach((id) => (enr.mastery[id].remediation = true))

    // retire the planned quiz (marked as taken), drop stale follow-ups
    if (isTopic) {
      const planned = tasks.find((t) => !t.done && t.type === 'topic-quiz' && t.topicId === sess.topicId)
      if (planned) done(planned, `${result} · below threshold`)
    } else {
      const planned = tasks.find((t) => !t.done && QUIZ_LIKE.includes(t.type) && t.subtopicId === sess.subtopicId)
      if (planned) done(planned, `${result} · below threshold`)
    }
    for (let i = tasks.length - 1; i >= 0; i--) {
      const t = tasks[i]
      if (t.done) continue
      const stale = (t.subtopicId && failingIds.has(t.subtopicId) && (QUIZ_LIKE.includes(t.type) || t.type === 'remediation')) || (isTopic && t.type === 'topic-quiz' && t.topicId === sess.topicId)
      if (stale) tasks.splice(i, 1)
    }

    const anchorTopic = isTopic ? course.topics.find((t) => t.id === sess.topicId) : topicOf(sess.subtopicId)
    const extra = failing.map((f) => makeTask('remediation', topicOf(f.subtopicId), { id: f.subtopicId }, `Remediation: ${f.title}`, MINUTES.remediation))
    extra.push(
      isTopic
        ? makeTask('topic-quiz', anchorTopic, null, `Retake topic quiz: ${anchorTopic.title}`, MINUTES['topic-quiz'])
        : makeTask('retake', anchorTopic, { id: sess.subtopicId }, `Retake quiz: ${subTitle(sess.subtopicId)}`, MINUTES.retake),
    )
    insertLater(tasks, extra, anchorTopic.id, isTopic ? 2 : 3)
    actions.shifted = repack(tasks, enr.plan.startDate, clock.todayISO(), enr.plan.minutesPerDay)
    actions.items = extra.map((t) => ({ title: t.title, type: t.type, date: t.date, day: t.day + 1 }))
    const retake = extra[extra.length - 1]
    addNotice(
      enr,
      'reschedule',
      `Scored ${score}% on ${sess.title.replace(/^(Quiz|Practice quiz|Topic quiz): /, '')}, below the ${thr}% threshold. ${failing.map((f) => f.title).join(', ')} moved to later in the plan with remediation material; retake scheduled for Day ${retake.day + 1}. ${actions.shifted ? `${actions.shifted} later ${actions.shifted === 1 ? 'task was' : 'tasks were'} shifted to rebalance the plan.` : 'The rest of the plan was recalculated.'}`,
    )
  }

  db().attempts.push({ id: uid('att'), enrollmentId: enr.id, userId: user.id, courseId: course.id, kind: sess.kind, title: sess.title, score, correct, total, passed, threshold: thr, ts: clock.now(), subtopicIds: Object.keys(per) })
  const dayStatus = checkDays(enr, course, touchedDays)
  save()
  const next = enr.plan.tasks.find((t) => !t.done)
  return {
    kind: sess.kind,
    courseId: course.id,
    title: sess.title,
    score,
    correct,
    total,
    passed,
    threshold: thr,
    review,
    bySubtopic,
    actions,
    dayStatus,
    nextTask: next ? { id: next.id, title: next.title, type: next.type, date: next.date, subtopicId: next.subtopicId, topicId: next.topicId } : null,
  }
}

/* ---------- Plan & tasks ---------- */

export function completeTask(user, courseId, taskId) {
  const enr = mustEnrollment(user, courseId)
  const t = enr.plan.tasks.find((x) => x.id === taskId)
  if (!t) throw new ApiError('Task not found.', 404)
  if (!['study', 'remediation'].includes(t.type)) throw new ApiError('Quizzes are completed by taking them.')
  if (!t.done) {
    finish(t, 'completed')
    const rec = enr.mastery[t.subtopicId]
    if (rec) rec.studied = true
  }
  const dayStatus = checkDays(enr, findCourse(courseId), new Set([t.day]))
  save()
  return { taskId, dayStatus }
}

/** Marks the first pending study/remediation task of a sub-topic as done (used by "Mark as studied"). */
export function completeSubtopicTask(user, courseId, subtopicId, type) {
  const enr = mustEnrollment(user, courseId)
  const t = enr.plan.tasks.find((x) => !x.done && x.subtopicId === subtopicId && x.type === type)
  if (!t) {
    const rec = enr.mastery[subtopicId]
    if (rec) rec.studied = true
    save()
    return { taskId: null, dayStatus: null }
  }
  return completeTask(user, courseId, t.id)
}

export function updatePlanSettings(user, courseId, { minutesPerDay }) {
  if (!MINUTES_OPTIONS.includes(minutesPerDay)) throw new ApiError('Choose a daily study time from the list.')
  const enr = mustEnrollment(user, courseId)
  enr.plan.minutesPerDay = minutesPerDay
  const moved = repack(enr.plan.tasks, enr.plan.startDate, clock.todayISO(), minutesPerDay)
  addNotice(enr, 'recalc', `Daily study time set to ${minutesPerDay} minutes. The remaining plan was recalculated${moved ? ` and ${moved} ${moved === 1 ? 'task moved' : 'tasks moved'} later` : ''}.`)
  save()
  return enrollmentDetail(enr)
}

/* ---------- Reads for the student UI ---------- */

export function catalog(user) {
  return db()
    .courses.filter((c) => c.status === 'published')
    .map((c) => {
      const s = structure(c.id)
      const enr = myEnrollment(user, c.id)
      return { ...s, topicCount: s.topics.length, subtopicCount: s.topics.reduce((n, t) => n + t.subtopics.length, 0), enrollment: enr ? enrollmentSummary(enr) : null }
    })
}

export function studentCourse(user, courseId) {
  const course = structure(courseId)
  const enr = myEnrollment(user, courseId)
  if (enr) refresh(enr)
  return { course, enrollment: enr ? enrollmentDetail(enr) : null }
}

export function getSubtopic(user, courseId, subtopicId) {
  const enr = mustEnrollment(user, courseId)
  const course = findCourse(courseId)
  const flat = allSubtopics(course)
  const idx = flat.findIndex((x) => x.sub.id === subtopicId)
  if (idx < 0) throw new ApiError('Sub-topic not found.', 404)
  const { topic, sub } = flat[idx]
  const thr = thresholdFor(courseId)
  const rec = enr.mastery[subtopicId]
  const nav = (x) => (x ? { id: x.sub.id, title: x.sub.title } : null)
  return {
    course: { id: course.id, code: course.code, title: course.title },
    topic: { id: topic.id, title: topic.title },
    subtopic: { id: sub.id, title: sub.title, description: sub.description, points: sub.points, summary: sub.summary, flashcards: sub.flashcards, remediation: sub.remediation },
    mastery: { value: rec.value, lastScore: rec.lastScore, attempts: rec.attempts, remediation: rec.remediation, studied: rec.studied, status: subStatus(rec, thr) },
    threshold: thr,
    tasks: enr.plan.tasks.filter((t) => t.subtopicId === subtopicId).map((t) => ({ ...t })),
    prev: nav(flat[idx - 1]),
    next: nav(flat[idx + 1]),
  }
}

export function dashboard(user) {
  const enrs = db().enrollments.filter((e) => e.userId === user.id)
  enrs.forEach(refresh)
  const summaries = enrs.map(enrollmentSummary)
  return {
    enrollments: summaries,
    today: summaries.flatMap((s) => s.todayTasks.map((t) => ({ ...t, courseId: s.courseId, courseCode: s.code, courseTitle: s.title }))),
    statuses: enrs
      .flatMap((e) => e.dayStatuses.map((d) => ({ ...d, courseId: e.courseId, courseCode: findCourse(e.courseId).code })))
      .sort((a, b) => b.ts - a.ts)
      .slice(0, 4),
    recent: db()
      .attempts.filter((a) => a.userId === user.id)
      .slice(-5)
      .reverse(),
  }
}

export function progress(user) {
  const enrs = db().enrollments.filter((e) => e.userId === user.id)
  enrs.forEach(refresh)
  return { enrollments: enrs.map(enrollmentDetail) }
}

export function practiceOptions(user) {
  return db()
    .enrollments.filter((e) => e.userId === user.id)
    .map((e) => {
      const c = findCourse(e.courseId)
      const thr = thresholdFor(c.id)
      return {
        courseId: c.id,
        code: c.code,
        title: c.title,
        subtopics: allSubtopics(c).map(({ topic, sub }) => ({ id: sub.id, title: sub.title, topic: topic.title, mastery: e.mastery[sub.id]?.value ?? 0, status: subStatus(e.mastery[sub.id], thr) })),
      }
    })
}
