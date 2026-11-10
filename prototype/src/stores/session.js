import { reactive } from 'vue'
import { api } from '../backend/index.js'

export const session = reactive({
  user: null,
  ready: false,
  async init() {
    if (this.ready) return
    try {
      this.user = await api.auth.me()
    } catch {
      this.user = null
    }
    this.ready = true
  },
  async login(email, password, portal) {
    this.user = await api.auth.login(email, password, portal)
    return this.user
  },
  async logout() {
    await api.auth.logout()
    this.user = null
  },
})

export const homeFor = (user) => (user.role === 'student' ? '/student' : user.role === 'faculty' ? '/faculty' : '/admin')
export const roleLabel = (role) => ({ student: 'Student', faculty: 'Faculty', admin: 'Management' })[role]
