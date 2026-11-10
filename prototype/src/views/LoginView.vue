<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Crest from '../components/Crest.vue'
import { api } from '../backend/index.js'
import { session, homeFor } from '../stores/session.js'

const router = useRouter()
const route = useRoute()
const portal = ref('student')
const email = ref('')
const password = ref('')
const show = ref(false)
const busy = ref(false)
const error = ref('')
const demos = ref([])

onMounted(async () => {
  demos.value = await api.auth.demoLogins()
})
const shown = computed(() => demos.value.filter((d) => d.portal === portal.value))

function setPortal(p) {
  portal.value = p
  error.value = ''
}
function fill(d) {
  email.value = d.email
  password.value = d.password
  error.value = ''
}
async function submit() {
  error.value = ''
  busy.value = true
  try {
    const user = await session.login(email.value, password.value, portal.value)
    const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith(`/${user.role === 'admin' ? 'admin' : user.role}`) ? route.query.redirect : homeFor(user)
    router.push(target)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
async function resetDemo() {
  if (!confirm('Reset all demo data (accounts, enrolments, courses) to its original state?')) return
  await api.resetDemo()
  location.reload()
}
</script>

<template>
  <div class="login">
    <aside class="login-brand">
      <div class="row" style="gap: 14px">
        <Crest :size="46" />
        <div>
          <div style="font-family: var(--serif); font-size: 26px; font-weight: 700; letter-spacing: -0.01em; line-height: 1">Gradient</div>
          <div class="xs" style="letter-spacing: 0.16em; text-transform: uppercase; color: #c9a9a0; margin-top: 5px; font-size: 10px; font-weight: 500">Learning Portal</div>
        </div>
      </div>
      <div>
        <h1>A study plan that <em>adapts</em> to every learner.</h1>
        <p>Faculty publish the syllabus. Students sit a short pre-test and receive a personal plan that reschedules itself when a topic needs more time.</p>
      </div>
      <div class="foot">Prototype · all data is simulated and stored in your browser.</div>
      <svg class="curve" viewBox="0 0 800 260" fill="none" aria-hidden="true" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="lc" x1="0" y1="0" x2="800" y2="0" gradientUnits="userSpaceOnUse"><stop stop-color="#f1c9b5" stop-opacity="0" /><stop offset=".45" stop-color="#f1c9b5" /><stop offset="1" stop-color="#ffffff" /></linearGradient>
        </defs>
        <line x1="0" y1="86" x2="800" y2="86" stroke="#fff" stroke-opacity=".22" stroke-dasharray="3 7" />
        <text x="24" y="76" fill="#c9a9a0" font-family="Public Sans, sans-serif" font-size="11" letter-spacing="1.6">PASS MARK</text>
        <path class="stroke" d="M0 236C110 236 150 214 230 190S360 150 430 118 560 66 640 54 760 44 800 42" stroke="url(#lc)" stroke-width="2.5" stroke-linecap="round" />
        <circle class="dot" style="animation-delay: 1s" cx="230" cy="190" r="5" fill="#f1c9b5" />
        <circle class="dot" style="animation-delay: 1.6s" cx="430" cy="118" r="5" fill="#f1c9b5" />
        <circle class="dot" style="animation-delay: 2.3s" cx="640" cy="54" r="6" fill="#fff" />
      </svg>
    </aside>

    <section class="login-form-wrap">
      <div class="login-card">
        <h2>Welcome back</h2>
        <p class="muted">Choose your portal and sign in with your university credentials.</p>
        <div class="seg" role="group" aria-label="Portal" style="margin: 8px 0 22px">
          <button type="button" :aria-pressed="portal === 'student'" @click="setPortal('student')">Student</button>
          <button type="button" :aria-pressed="portal === 'staff'" @click="setPortal('staff')">Faculty / Management</button>
        </div>

        <form @submit.prevent="submit" novalidate>
          <div class="field">
            <label for="email">University email</label>
            <input id="email" v-model="email" class="input" type="email" autocomplete="username" placeholder="name@gradient.edu" required />
          </div>
          <div class="field">
            <label for="pw">Password</label>
            <div class="row" style="gap: 8px">
              <input id="pw" v-model="password" class="input" :type="show ? 'text' : 'password'" autocomplete="current-password" required />
              <button type="button" class="btn secondary sm" :aria-pressed="show" @click="show = !show">{{ show ? 'Hide' : 'Show' }}</button>
            </div>
          </div>
          <div v-if="error" class="callout bad" role="alert" style="margin-bottom: 16px">{{ error }}</div>
          <button class="btn lg" type="submit" style="width: 100%" :disabled="busy || !email || !password">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
        </form>

        <div class="demo-box">
          <h4>Demo accounts</h4>
          <button v-for="d in shown" :key="d.email" type="button" class="demo-row" @click="fill(d)">
            <span><b>{{ d.name }}</b><small>{{ d.note }}</small></span>
            <small>Use</small>
          </button>
          <p class="xs muted" style="margin: 10px 0 0">Click an account to fill the form. Student password <code>student123</code>, faculty <code>faculty123</code>, management <code>admin123</code>.</p>
        </div>
        <p class="xs" style="margin-top: 18px; text-align: center"><button type="button" class="link-btn faint" @click="resetDemo">Reset demo data</button></p>
      </div>
    </section>
  </div>
</template>
