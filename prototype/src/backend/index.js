// Public surface of the mock backend. Every call is async, authenticated by the
// stored session token, and returns plain JSON, like a REST API would.
import { db, resetDb } from './db.js'
import { runSeed } from './seed.js'
import { ApiError, clone } from './util.js'
import * as auth from './services/auth.js'
import * as courses from './services/courses.js'
import * as learning from './services/learning.js'
import * as syllabus from './services/syllabus.js'
import * as settings from './services/settings.js'
import * as metrics from './services/metrics.js'
import { demoLogins } from './data/users.js'

const LATENCY = 120
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

/** Wrap a handler: simulate latency, enforce roles, normalise errors. */
const endpoint = (roles, handler) => async (...args) => {
  await wait(LATENCY)
  try {
    runSeed()
    const user = roles === 'public' ? null : auth.requireUser(roles)
    return clone(handler(user, ...args))
  } catch (e) {
    if (e instanceof ApiError) throw e
    console.error(e)
    throw new ApiError('Something went wrong on the server.', 500)
  }
}

const STAFF = ['faculty', 'admin']

export const api = {
  auth: {
    login: endpoint('public', (_u, email, password, portal) => auth.login(email, password, portal)),
    logout: endpoint('public', () => auth.logout()),
    me: endpoint('public', () => {
      const u = auth.currentUser()
      return u ? auth.toPublicUser(u) : null
    }),
    demoLogins: endpoint('public', () => demoLogins),
  },
  student: {
    dashboard: endpoint(['student'], (u) => learning.dashboard(u)),
    catalog: endpoint(['student'], (u) => learning.catalog(u)),
    course: endpoint(['student'], (u, courseId) => learning.studentCourse(u, courseId)),
    subtopic: endpoint(['student'], (u, courseId, subtopicId) => learning.getSubtopic(u, courseId, subtopicId)),
    startQuiz: endpoint(['student'], (u, req) => learning.startQuiz(u, req)),
    submitQuiz: endpoint(['student'], (u, quizId, answers) => learning.submitQuiz(u, quizId, answers)),
    completeStudy: endpoint(['student'], (u, courseId, subtopicId, type) => learning.completeSubtopicTask(u, courseId, subtopicId, type)),
    completeTask: endpoint(['student'], (u, courseId, taskId) => learning.completeTask(u, courseId, taskId)),
    setPlanMinutes: endpoint(['student'], (u, courseId, minutes) => learning.updatePlanSettings(u, courseId, { minutesPerDay: minutes })),
    progress: endpoint(['student'], (u) => learning.progress(u)),
    practiceOptions: endpoint(['student'], (u) => learning.practiceOptions(u)),
  },
  faculty: {
    courses: endpoint(STAFF, (u) => courses.listForStaff(u)),
    course: endpoint(STAFF, (u, id) => courses.getForStaff(u, id)),
    saveCourse: endpoint(STAFF, (u, course) => courses.saveCourse(u, course)),
    setStatus: endpoint(STAFF, (u, id, status) => courses.setStatus(u, id, status)),
    removeCourse: endpoint(STAFF, (u, id) => courses.removeCourse(u, id)),
    sampleSyllabus: endpoint(STAFF, () => syllabus.SAMPLE_SYLLABUS),
    analyzeSyllabus: endpoint(STAFF, (_u, payload) => syllabus.analyze(payload)),
    deriveSubtopics: endpoint(STAFF, (u, payload) => syllabus.derive(u, payload)),
  },
  admin: {
    overview: endpoint(['admin'], () => metrics.adminOverview()),
    student: endpoint(['admin'], (_u, id) => {
      const r = metrics.adminStudent(id)
      if (!r) throw new ApiError('Student not found.', 404)
      return r
    }),
    settings: endpoint(['admin'], () => settings.getSettings()),
    saveSettings: endpoint(['admin'], (_u, payload) => settings.updateSettings(payload)),
  },
  /** Demo helper: wipe local data and re-seed it. */
  resetDemo: async () => {
    resetDb()
    runSeed()
    return true
  },
}

export const ready = () => db().seeded
