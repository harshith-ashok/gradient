<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Crest from './Crest.vue'
import Icon from './Icon.vue'
import { session, roleLabel } from '../stores/session.js'

const route = useRoute()
const router = useRouter()

const NAV = {
  student: [
    { to: '/student', label: 'Dashboard', exact: true },
    { to: '/student/courses', label: 'Courses' },
    { to: '/student/practice', label: 'Practice' },
    { to: '/student/progress', label: 'Progress' },
  ],
  faculty: [
    { to: '/faculty', label: 'My courses', exact: true },
    { to: '/faculty/upload', label: 'Upload syllabus' },
  ],
  admin: [
    { to: '/admin', label: 'Dashboard', exact: true },
    { to: '/admin/settings', label: 'Settings' },
  ],
}
const initials = computed(() => (session.user?.name || '').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase())
const links = computed(() => NAV[session.user?.role] || [])
const active = (l) => (l.exact ? route.path === l.to : route.path.startsWith(l.to))

async function signOut() {
  await session.logout()
  router.push('/login')
}
</script>

<template>
  <header class="shell-top">
    <div class="inner">
      <RouterLink to="/" class="wordmark" aria-label="Gradient home">
        <Crest />
        <span><b>Gradient</b><small>Learning Portal</small></span>
      </RouterLink>
      <nav class="nav" aria-label="Primary">
        <RouterLink v-for="l in links" :key="l.to" :to="l.to" :class="{ active: active(l) }">{{ l.label }}</RouterLink>
      </nav>
      <div v-if="session.user" class="userbox">
        <div class="avatar" aria-hidden="true">{{ initials }}</div>
        <div class="who">
          <b>{{ session.user.name }}</b>
          <small>{{ roleLabel(session.user.role) }}</small>
        </div>
        <button class="btn-ghost-light" type="button" @click="signOut">Sign out <Icon name="out" :size="14" /></button>
      </div>
    </div>
  </header>
  <main class="main" :class="{ wide: route.meta.wide }">
    <div :key="route.path" class="page"><RouterView /></div>
  </main>
  <footer v-if="!route.meta.wide" class="footer">Gradient Learning Portal · Prototype with simulated data</footer>
</template>
