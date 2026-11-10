// A tiny document store that stands in for a real database.
// State lives in localStorage so changes survive a page refresh.
import { users } from './data/users.js'
import { courseC } from './data/course-c.js'
import { courseCpp } from './data/course-cpp.js'
import { courseEcon } from './data/course-econ.js'
import { DAY_MS, toISO, clone } from './util.js'

const KEY = 'gradient.db.v2'
export const TOKEN_KEY = 'gradient.token'
const memory = {}

export const storage = {
  get(k) {
    try {
      return localStorage.getItem(k)
    } catch {
      return memory[k] ?? null
    }
  },
  set(k, v) {
    try {
      localStorage.setItem(k, v)
    } catch {
      memory[k] = v
    }
  },
  remove(k) {
    try {
      localStorage.removeItem(k)
    } catch {
      delete memory[k]
    }
  },
}

/** Time source. The seed script shifts it so demo data looks lived-in. */
export const clock = {
  offsetMs: 0,
  now() {
    return Date.now() + this.offsetMs
  },
  todayISO() {
    return toISO(this.now())
  },
  setDaysAgo(n) {
    this.offsetMs = -n * DAY_MS
  },
  reset() {
    this.offsetMs = 0
  },
}

const initialState = () => ({
  version: 1,
  seeded: false,
  users: clone(users),
  courses: clone([courseC, courseCpp, courseEcon]),
  settings: { globalThreshold: 70, perCourse: {} },
  enrollments: [],
  attempts: [],
  sessions: {},
  drafts: {},
})

let state = null

export function db() {
  if (!state) {
    const raw = storage.get(KEY)
    try {
      state = raw ? JSON.parse(raw) : null
    } catch {
      state = null
    }
    if (!state || state.version !== 1) state = initialState()
  }
  return state
}

export function save() {
  if (state) storage.set(KEY, JSON.stringify(state))
}

/** Wipe everything and return to a pristine (unseeded) state. */
export function resetDb() {
  state = initialState()
  storage.remove(TOKEN_KEY)
  save()
}
