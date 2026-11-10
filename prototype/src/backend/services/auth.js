import { db, save, storage, TOKEN_KEY, clock } from '../db.js'
import { demoHash } from '../hash.js'
import { ApiError, uid } from '../util.js'

const publicUser = (u) => {
  const { passwordHash: _omit, ...rest } = u
  return rest
}

/** portal: 'student' | 'staff' (faculty or management) */
export function login(email, password, portal) {
  const user = db().users.find((u) => u.email.toLowerCase() === String(email).trim().toLowerCase())
  if (!user || user.passwordHash !== demoHash(String(password))) {
    throw new ApiError('Incorrect email or password.', 401)
  }
  const isStaff = user.role === 'faculty' || user.role === 'admin'
  if (portal === 'student' && isStaff) {
    throw new ApiError('This account belongs to the Faculty / Management portal.', 403)
  }
  if (portal === 'staff' && !isStaff) {
    throw new ApiError('This account belongs to the Student portal.', 403)
  }
  const token = uid('tok')
  db().sessions[token] = { userId: user.id, createdAt: clock.now() }
  save()
  storage.set(TOKEN_KEY, token)
  return publicUser(user)
}

export function logout() {
  const token = storage.get(TOKEN_KEY)
  if (token && db().sessions[token]) {
    delete db().sessions[token]
    save()
  }
  storage.remove(TOKEN_KEY)
}

/** Resolve the signed-in user from the stored session token, or null. */
export function currentUser() {
  const token = storage.get(TOKEN_KEY)
  const session = token && db().sessions[token]
  if (!session) return null
  return db().users.find((u) => u.id === session.userId) || null
}

export function requireUser(roles) {
  const user = currentUser()
  if (!user) throw new ApiError('Please sign in to continue.', 401)
  if (roles && !roles.includes(user.role)) throw new ApiError('You do not have access to this area.', 403)
  return user
}

export const toPublicUser = publicUser
