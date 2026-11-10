import { db, save } from '../db.js'
import { ApiError, clone } from '../util.js'

export const MIN_THRESHOLD = 40
export const MAX_THRESHOLD = 100

export function thresholdFor(courseId) {
  const s = db().settings
  const own = s.perCourse[courseId]
  return typeof own === 'number' ? own : s.globalThreshold
}

export function getSettings() {
  const s = db().settings
  return {
    globalThreshold: s.globalThreshold,
    perCourse: clone(s.perCourse),
    courses: db().courses.map((c) => ({
      id: c.id,
      code: c.code,
      title: c.title,
      status: c.status,
      override: typeof s.perCourse[c.id] === 'number' ? s.perCourse[c.id] : null,
      effective: thresholdFor(c.id),
    })),
  }
}

export function updateSettings({ globalThreshold, perCourse }) {
  const valid = (n) => Number.isInteger(n) && n >= MIN_THRESHOLD && n <= MAX_THRESHOLD
  if (!valid(globalThreshold)) throw new ApiError(`Threshold must be a whole number from ${MIN_THRESHOLD} to ${MAX_THRESHOLD}.`)
  const clean = {}
  for (const [id, v] of Object.entries(perCourse || {})) {
    if (v === null || v === undefined) continue
    if (!valid(v)) throw new ApiError(`Course threshold must be a whole number from ${MIN_THRESHOLD} to ${MAX_THRESHOLD}.`)
    clean[id] = v
  }
  db().settings = { globalThreshold, perCourse: clean }
  save()
  return getSettings()
}
