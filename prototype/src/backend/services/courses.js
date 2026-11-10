import { db, save } from '../db.js'
import { ApiError, uid, clone } from '../util.js'
import { refreshGenerated } from './contentgen.js'
import { thresholdFor } from './settings.js'

export const findCourse = (id) => db().courses.find((c) => c.id === id)
export const allSubtopics = (course) => course.topics.flatMap((t) => t.subtopics.map((s) => ({ topic: t, sub: s })))
const counts = (c) => ({ topics: c.topics.length, subtopics: c.topics.reduce((n, t) => n + t.subtopics.length, 0) })

export function listForStaff(user) {
  return db()
    .courses.filter((c) => user.role === 'admin' || c.instructorId === user.id)
    .map((c) => ({
      id: c.id,
      code: c.code,
      title: c.title,
      department: c.department,
      status: c.status,
      accent: c.accent,
      source: c.source,
      ...counts(c),
      enrolled: db().enrollments.filter((e) => e.courseId === c.id).length,
      threshold: thresholdFor(c.id),
    }))
}

export function getForStaff(user, id) {
  const c = findCourse(id)
  if (!c) throw new ApiError('Course not found.', 404)
  if (user.role === 'faculty' && c.instructorId !== user.id) throw new ApiError('You can only edit your own courses.', 403)
  return clone(c)
}

export function saveCourse(user, incoming) {
  const existing = findCourse(incoming.id)
  if (!existing) throw new ApiError('Course not found.', 404)
  if (user.role === 'faculty' && existing.instructorId !== user.id) throw new ApiError('You can only edit your own courses.', 403)
  if (!incoming.title?.trim() || !incoming.code?.trim()) throw new ApiError('Course code and title are required.')
  for (const t of incoming.topics) {
    if (!t.title?.trim()) throw new ApiError('Every topic needs a title.')
    for (const s of t.subtopics) if (!s.title?.trim()) throw new ApiError('Every sub-topic needs a title.')
  }
  const next = clone(incoming)
  next.instructorId = existing.instructorId
  for (const t of next.topics) {
    t.id ||= uid('t')
    for (const s of t.subtopics) {
      s.id ||= uid('s')
      s.points = (s.points || []).map((p) => p.trim()).filter(Boolean)
    }
  }
  refreshGenerated(next)
  Object.assign(existing, next)
  save()
  return clone(existing)
}

export function setStatus(user, id, status) {
  const c = getForStaff(user, id)
  if (status === 'published') {
    if (!c.topics.length) throw new ApiError('Add at least one topic before publishing.')
    for (const t of c.topics) {
      if (!t.subtopics.length) throw new ApiError(`Topic “${t.title}” has no sub-topics.`)
      for (const s of t.subtopics) if (!s.questions?.length) throw new ApiError(`Sub-topic “${s.title}” has no quiz questions yet. Add key points so questions can be generated.`)
    }
  }
  findCourse(id).status = status
  save()
  return { id, status }
}

export function removeCourse(user, id) {
  const c = getForStaff(user, id)
  if (db().enrollments.some((e) => e.courseId === c.id)) throw new ApiError('Students are enrolled in this course, so it cannot be deleted.')
  db().courses = db().courses.filter((x) => x.id !== id)
  save()
  return { id }
}

/** Topics and sub-topics without answers, for students browsing a course. */
export function structure(courseId) {
  const c = findCourse(courseId)
  if (!c || c.status !== 'published') throw new ApiError('Course not found.', 404)
  return {
    id: c.id,
    code: c.code,
    title: c.title,
    department: c.department,
    credits: c.credits,
    level: c.level,
    accent: c.accent,
    description: c.description,
    instructor: db().users.find((u) => u.id === c.instructorId)?.name || 'Faculty',
    threshold: thresholdFor(c.id),
    topics: c.topics.map((t) => ({
      id: t.id,
      title: t.title,
      subtopics: t.subtopics.map((s) => ({ id: s.id, title: s.title, description: s.description })),
    })),
  }
}
