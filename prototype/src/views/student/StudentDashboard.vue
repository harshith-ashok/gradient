<script setup>
import { api } from '../../backend/index.js'
import { session } from '../../stores/session.js'
import { useAsync } from '../../lib/useAsync.js'
import { firstName, fmtTs, relDay, ENR_STATUS } from '../../lib/format.js'
import LoadState from '../../components/LoadState.vue'
import RingProgress from '../../components/RingProgress.vue'
import MeterBar from '../../components/MeterBar.vue'
import TaskRow from '../../components/TaskRow.vue'
import Icon from '../../components/Icon.vue'
import { computed } from 'vue'

const { data, loading, error } = useAsync(() => api.student.dashboard())
const today = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const avg = computed(() => {
  const e = data.value?.enrollments || []
  return e.length ? Math.round(e.reduce((n, x) => n + x.overall, 0) / e.length) : 0
})
const left = computed(() => (data.value?.today || []).filter((t) => !t.done).length)
const tone = (e) => (e.overall >= e.threshold ? 'ok' : e.overall >= e.threshold - 25 ? 'warn' : 'bad')
</script>

<template>
  <section class="hero">
    <svg class="curve" viewBox="0 0 560 220" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="hc" x1="0" y1="0" x2="800" y2="0" gradientUnits="userSpaceOnUse"><stop stop-color="#f1c9b5" stop-opacity="0" /><stop offset=".45" stop-color="#f1c9b5" /><stop offset="1" stop-color="#ffffff" /></linearGradient>
      </defs>
      <line x1="0" y1="70" x2="560" y2="70" stroke="#fff" stroke-opacity=".18" stroke-dasharray="3 7" />
      <path class="stroke" d="M0 200C90 200 130 176 200 150S320 104 380 80 480 44 560 36" stroke="url(#hc)" stroke-width="2.5" stroke-linecap="round" />
    </svg>
    <div class="eyebrow">{{ today }}</div>
    <h1>Welcome back, <em>{{ firstName(session.user.name) }}</em></h1>
    <p>Your plan reschedules itself when a topic needs more time. Here is where you stand today.</p>
    <div class="actions">
      <RouterLink to="/student/courses" class="btn secondary">Browse courses</RouterLink>
      <RouterLink to="/student/practice" class="btn gold">Quiz me on… <Icon name="arrow" /></RouterLink>
    </div>
    <div v-if="data && data.enrollments.length" class="hero-stats">
      <div><div class="v">{{ avg }}<small>%</small></div><div class="l">Average mastery</div></div>
      <div><div class="v">{{ left }}</div><div class="l">Tasks left today</div></div>
      <div><div class="v">{{ data.enrollments.length }}</div><div class="l">{{ data.enrollments.length === 1 ? 'Course' : 'Courses' }} in progress</div></div>
    </div>
  </section>

  <LoadState :loading="loading" :error="error">
    <template v-if="data">
      <div v-if="!data.enrollments.length" class="card empty">
        <h3>You have not started a course yet</h3>
        <p>Pick a course from the catalogue. You will take a short pre-test and receive a personalised study plan.</p>
        <RouterLink to="/student/courses" class="btn">Choose a course</RouterLink>
      </div>

      <template v-else>
        <div class="grid cols-2" style="align-items: start">
          <div class="card">
            <div class="card-head"><h2>Today’s agenda</h2><span class="badge navy plain">{{ data.today.filter((t) => !t.done).length }} to do</span></div>
            <div class="card-body" style="padding-top: 6px; padding-bottom: 6px">
              <p v-if="!data.today.length" class="muted" style="margin: 14px 0">Nothing scheduled for today. You can work ahead from your study plan.</p>
              <TaskRow v-for="t in data.today" :key="t.id" :task="t" :course-id="t.courseId" :show-course="t.courseCode" />
            </div>
          </div>

          <div class="card">
            <div class="card-head"><h2>End-of-day status</h2></div>
            <div class="card-body" style="padding-top: 6px; padding-bottom: 6px">
              <p v-if="!data.statuses.length" class="muted" style="margin: 14px 0">Finish every task in a day to receive your daily status.</p>
              <div v-for="s in data.statuses" :key="s.id" class="task done">
                <span class="tick">✓</span>
                <div class="grow">
                  <div class="t-title" style="text-decoration: none; color: var(--ink)">{{ s.message }}</div>
                  <div class="t-meta">{{ s.courseCode }} · {{ relDay(s.date) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <section class="section" style="margin-top: 56px">
          <div class="section-head"><h2>My courses</h2></div>
          <div class="grid auto">
            <article v-for="e in data.enrollments" :key="e.courseId" class="card course-card" :style="{ '--accent': e.accent }">
              <div class="cc-top">
                <div class="row" style="align-items: flex-start">
                  <div class="grow">
                    <div class="code">{{ e.code }}</div>
                    <h3>{{ e.title }}</h3>
                    <span class="badge" :class="e.status === 'attention' ? 'warn' : e.status === 'completed' ? 'ok' : 'info'">{{ ENR_STATUS[e.status] }}</span>
                  </div>
                  <RingProgress :value="e.overall" :tone="tone(e)" />
                </div>
                <div style="margin-top: 16px" class="stack">
                  <div v-for="t in e.topics" :key="t.id">
                    <div class="row between xs muted" style="margin-bottom: 4px"><span>{{ t.title }}</span><span class="num">{{ t.mastery }}%</span></div>
                    <MeterBar :value="t.mastery" :threshold="e.threshold" thin :label="t.title" />
                  </div>
                </div>
              </div>
              <div class="cc-foot">
                <span class="small muted">{{ e.upcoming[0] ? `Next: ${e.upcoming[0].title}` : 'Plan complete' }}</span>
                <RouterLink :to="`/student/courses/${e.courseId}`" class="btn sm">Continue</RouterLink>
              </div>
            </article>
          </div>
        </section>

        <section v-if="data.recent.length" class="section">
          <div class="section-head"><h2>Recent results</h2><RouterLink to="/student/progress" class="small">Full progress <Icon name="arrow" :size="13" /></RouterLink></div>
          <div class="card table-wrap">
            <table class="table">
              <thead><tr><th>When</th><th>Assessment</th><th class="num">Score</th><th>Result</th></tr></thead>
              <tbody>
                <tr v-for="a in data.recent" :key="a.id">
                  <td class="small muted" style="white-space: nowrap">{{ fmtTs(a.ts) }}</td>
                  <td>{{ a.title }}</td>
                  <td class="num">{{ a.score }}%</td>
                  <td><span class="badge" :class="a.passed === null ? 'navy' : a.passed ? 'ok' : 'bad'">{{ a.passed === null ? 'Diagnostic' : a.passed ? 'Passed' : 'Below pass mark' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </template>
  </LoadState>
</template>
