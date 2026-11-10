// Read-only aggregations used by the student and admin dashboards.
import { db, clock } from '../db.js'
import { avg, dayDiff } from '../util.js'
import { thresholdFor } from './settings.js'

const course = (id) => db().courses.find((c) => c.id === id)

export function subStatus(rec, threshold) {
  if (!rec) return 'new'
  if (rec.remediation) return 'review'
  if (rec.lastScore != null && rec.lastScore >= threshold) return 'mastered'
  if (rec.studied || rec.attempts > 0) return 'learning'
  return 'new'
}

export function enrollmentSummary(enr) {
  const c = course(enr.courseId)
  const thr = thresholdFor(c.id)
  const subs = c.topics.flatMap((t) => t.subtopics)
  const mv = (s) => enr.mastery[s.id]?.value ?? 0
  const overall = avg(subs.map(mv))
  const pending = enr.plan.tasks.filter((t) => !t.done)
  const today = clock.todayISO()
  const myAttempts = db().attempts.filter((a) => a.enrollmentId === enr.id)
  const remediationCount = subs.filter((s) => enr.mastery[s.id]?.remediation).length
  const allMastered = subs.every((s) => subStatus(enr.mastery[s.id], thr) === 'mastered')
  return {
    enrollmentId: enr.id,
    courseId: c.id,
    code: c.code,
    title: c.title,
    accent: c.accent,
    overall,
    threshold: thr,
    topics: c.topics.map((t) => ({ id: t.id, title: t.title, mastery: avg(t.subtopics.map(mv)) })),
    upcoming: pending.slice(0, 4).map((t) => ({ id: t.id, title: t.title, type: t.type, date: t.date, minutes: t.minutes })),
    pendingCount: pending.length,
    todayTasks: enr.plan.tasks.filter((t) => t.date === today).map((t) => ({ ...t })),
    planDone: enr.plan.tasks.filter((t) => t.done).length,
    planTotal: enr.plan.tasks.length,
    remediationCount,
    attempts: myAttempts.length,
    lastActivity: myAttempts.length ? myAttempts[myAttempts.length - 1].ts : enr.createdAt,
    pretestScore: enr.pretest.score,
    latestDayStatus: enr.dayStatuses[enr.dayStatuses.length - 1] || null,
    status: allMastered && !pending.length ? 'completed' : remediationCount ? 'attention' : 'on-track',
    dayNumber: dayDiff(enr.plan.startDate, today) + 1,
  }
}

export function enrollmentDetail(enr) {
  const c = course(enr.courseId)
  const thr = thresholdFor(c.id)
  const sum = enrollmentSummary(enr)
  return {
    ...sum,
    startDate: enr.plan.startDate,
    minutesPerDay: enr.plan.minutesPerDay,
    notices: enr.plan.notices.slice().reverse(),
    tasks: enr.plan.tasks.map((t) => ({ ...t })),
    dayStatuses: enr.dayStatuses.slice().reverse(),
    pretest: enr.pretest,
    topicDetail: c.topics.map((t) => ({
      id: t.id,
      title: t.title,
      mastery: avg(t.subtopics.map((s) => enr.mastery[s.id]?.value ?? 0)),
      subtopics: t.subtopics.map((s) => {
        const rec = enr.mastery[s.id]
        return { id: s.id, title: s.title, mastery: rec?.value ?? 0, lastScore: rec?.lastScore ?? null, attempts: rec?.attempts ?? 0, status: subStatus(rec, thr) }
      }),
    })),
    history: db()
      .attempts.filter((a) => a.enrollmentId === enr.id)
      .slice()
      .reverse()
      .map((a) => ({ ...a })),
  }
}

/** Everything the admin dashboard needs: one row per student and course. */
export function adminOverview() {
  const students = db().users.filter((u) => u.role === 'student')
  const rows = []
  for (const s of students) {
    const mine = db().enrollments.filter((e) => e.userId === s.id)
    if (!mine.length) rows.push({ student: pub(s), enrollment: null })
    for (const e of mine) rows.push({ student: pub(s), enrollment: enrollmentSummary(e) })
  }
  const enrolled = rows.filter((r) => r.enrollment)
  const courses = db().courses.filter((c) => c.status === 'published').map((c) => {
    const es = enrolled.filter((r) => r.enrollment.courseId === c.id)
    return { id: c.id, code: c.code, title: c.title, enrolled: es.length, average: avg(es.map((r) => r.enrollment.overall)), threshold: thresholdFor(c.id) }
  })
  return {
    kpis: {
      students: students.length,
      activeLearners: new Set(enrolled.map((r) => r.student.id)).size,
      averageProgress: avg(enrolled.map((r) => r.enrollment.overall)),
      needAttention: enrolled.filter((r) => r.enrollment.status === 'attention').length,
    },
    courses,
    rows,
  }
}

export function adminStudent(id) {
  const u = db().users.find((x) => x.id === id && x.role === 'student')
  if (!u) return null
  return { student: pub(u), enrollments: db().enrollments.filter((e) => e.userId === id).map(enrollmentDetail) }
}

const pub = (u) => ({ id: u.id, name: u.name, email: u.email, studentId: u.studentId, program: u.program, year: u.year })
