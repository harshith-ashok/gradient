export const DAY_MS = 864e5

export const pad = (n) => String(n).padStart(2, '0')
export const toISO = (ms) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
const parseISO = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}
export const dayDiff = (fromISO, toISOStr) =>
  Math.round((parseISO(toISOStr) - parseISO(fromISO)) / DAY_MS)
export const addDaysISO = (iso, n) => {
  const d = parseISO(iso)
  d.setDate(d.getDate() + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

let counter = 0
export const uid = (prefix = 'id') =>
  `${prefix}-${Date.now().toString(36)}${(counter++).toString(36)}${Math.random().toString(36).slice(2, 6)}`

export const shuffle = (arr) => {
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)))
export const avg = (nums) => (nums.length ? Math.round(nums.reduce((s, n) => s + n, 0) / nums.length) : 0)

export class ApiError extends Error {
  constructor(message, status = 400) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}
