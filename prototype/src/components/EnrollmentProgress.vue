<script setup>
import { computed } from 'vue'
import RingProgress from './RingProgress.vue'
import MeterBar from './MeterBar.vue'
import TaskRow from './TaskRow.vue'
import { STATUS_LABEL, ENR_STATUS, fmtTs, relDay } from '../lib/format.js'

const props = defineProps({ e: Object, readonly: Boolean })
const pending = computed(() => props.e.tasks.filter((t) => !t.done).slice(0, 6))
const tone = (v) => (v >= props.e.threshold ? 'ok' : v >= props.e.threshold - 25 ? 'warn' : 'bad')
const statusTone = { new: '', learning: 'info', review: 'warn', mastered: 'ok' }
const histTone = (a) => (a.passed === null ? 'navy' : a.passed ? 'ok' : 'bad')
</script>

<template>
  <section class="stack" :style="{ '--accent': e.accent }">
    <div class="card accent card-pad">
      <div class="row wrap" style="gap: 24px">
        <RingProgress :value="e.overall" :size="96" :stroke="8" :tone="tone(e.overall)" />
        <div class="grow">
          <div class="xs muted" style="letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600">{{ e.code }}</div>
          <h2 style="margin: 2px 0 6px">{{ e.title }}</h2>
          <div class="row wrap">
            <span class="badge" :class="e.status === 'attention' ? 'warn' : e.status === 'completed' ? 'ok' : 'info'">{{ ENR_STATUS[e.status] }}</span>
            <span class="small muted">Pre-test {{ e.pretestScore }}% · {{ e.planDone }} of {{ e.planTotal }} plan tasks done · pass mark {{ e.threshold }}%</span>
          </div>
        </div>
        <slot name="actions" />
      </div>
      <div v-if="e.latestDayStatus" class="callout ok" style="margin-top: 16px">
        <b>{{ e.latestDayStatus.message }}</b> <span class="muted">· {{ relDay(e.latestDayStatus.date) }}</span>
      </div>
    </div>

    <div class="grid cols-2" style="align-items: start">
      <div class="card">
        <div class="card-head"><h3>Mastery by topic</h3><span class="xs muted">Gold marker = pass mark</span></div>
        <div class="card-body stack">
          <div v-for="t in e.topicDetail" :key="t.id">
            <div class="row between small" style="margin-bottom: 6px"><b>{{ t.title }}</b><span class="num">{{ t.mastery }}%</span></div>
            <MeterBar :value="t.mastery" :threshold="e.threshold" :label="t.title" />
            <ul style="list-style: none; padding: 0; margin: 10px 0 0" class="small">
              <li v-for="s in t.subtopics" :key="s.id" class="row between" style="padding: 3px 0; gap: 8px">
                <RouterLink v-if="!readonly" :to="`/student/courses/${e.courseId}/subtopics/${s.id}`" class="grow">{{ s.title }}</RouterLink>
                <span v-else class="grow">{{ s.title }}</span>
                <span class="badge" :class="statusTone[s.status]">{{ STATUS_LABEL[s.status] }}</span>
                <span class="num" style="min-width: 36px; text-align: right">{{ s.mastery }}%</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="stack">
        <div class="card">
          <div class="card-head"><h3>Upcoming tasks</h3><span class="xs muted">{{ e.pendingCount }} remaining</span></div>
          <div class="card-body" style="padding-top: 6px; padding-bottom: 6px">
            <template v-if="pending.length">
              <TaskRow v-for="t in pending" :key="t.id" :task="t" :course-id="e.courseId" show-date :locked="readonly" />
            </template>
            <p v-else class="muted small" style="margin: 12px 0">No tasks remaining.</p>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><h3>Daily status</h3></div>
          <div class="card-body" style="padding-top: 6px; padding-bottom: 6px">
            <p v-if="!e.dayStatuses.length" class="muted small" style="margin: 12px 0">No days completed yet.</p>
            <div v-for="d in e.dayStatuses" :key="d.id" class="task done" style="text-decoration: none">
              <span class="tick">✓</span>
              <div class="grow"><div class="t-title" style="text-decoration: none; color: var(--ink)">{{ d.message }}</div><div class="t-meta">{{ relDay(d.date) }}</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-head"><h3>Quiz history</h3><span class="xs muted">{{ e.history.length }} attempts</span></div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>When</th><th>Assessment</th><th class="num">Score</th><th>Result</th></tr></thead>
          <tbody>
            <tr v-for="a in e.history.slice(0, 12)" :key="a.id">
              <td class="small muted" style="white-space: nowrap">{{ fmtTs(a.ts) }}</td>
              <td>{{ a.title }}</td>
              <td class="num">{{ a.score }}%</td>
              <td><span class="badge" :class="histTone(a)">{{ a.passed === null ? 'Diagnostic' : a.passed ? 'Passed' : 'Below pass mark' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
