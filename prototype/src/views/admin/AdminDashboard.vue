<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync } from '../../lib/useAsync.js'
import { ENR_STATUS, relDay } from '../../lib/format.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'
import MeterBar from '../../components/MeterBar.vue'

const router = useRouter()
const { data, loading, error } = useAsync(() => api.admin.overview())
const course = ref('all')
const status = ref('all')
const search = ref('')

const rows = computed(() => {
  const q = search.value.trim().toLowerCase()
  return (data.value?.rows || []).filter((r) => {
    if (q && !`${r.student.name} ${r.student.email} ${r.student.studentId}`.toLowerCase().includes(q)) return false
    if (course.value !== 'all' && r.enrollment?.courseId !== course.value) return false
    if (status.value !== 'all' && r.enrollment?.status !== status.value) return false
    return true
  })
})
const tone = (v, thr) => (v >= thr ? 'ok' : v >= thr - 25 ? 'warn' : 'bad')
const open = (r) => router.push(`/admin/students/${r.student.id}`)
const statusBadge = { 'on-track': 'info', attention: 'warn', completed: 'ok' }
</script>

<template>
  <PageHeader eyebrow="Management" title="Student progress" lede="Overall progress, per-topic mastery and upcoming tasks for every student.">
    <template #actions><RouterLink to="/admin/settings" class="btn secondary">Quiz pass mark settings</RouterLink></template>
  </PageHeader>

  <LoadState :loading="loading" :error="error">
    <template v-if="data">
      <div class="grid cols-4" style="margin-bottom: 24px">
        <div class="card kpi"><div class="v">{{ data.kpis.students }}</div><div class="l">Students registered</div></div>
        <div class="card kpi"><div class="v">{{ data.kpis.activeLearners }}</div><div class="l">Students enrolled in a course</div></div>
        <div class="card kpi"><div class="v">{{ data.kpis.averageProgress }}%</div><div class="l">Average overall progress</div></div>
        <div class="card kpi"><div class="v" :style="{ color: data.kpis.needAttention ? 'var(--warn)' : '' }">{{ data.kpis.needAttention }}</div><div class="l">Enrolments needing attention</div></div>
      </div>

      <div class="card" style="margin-bottom: 24px">
        <div class="card-head"><h3>Courses</h3></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Course</th><th class="num">Enrolled</th><th style="width: 30%">Average progress</th><th class="num">Pass mark</th></tr></thead>
            <tbody>
              <tr v-for="c in data.courses" :key="c.id">
                <td><b>{{ c.code }}</b> · {{ c.title }}</td>
                <td class="num">{{ c.enrolled }}</td>
                <td><div class="row"><div class="grow"><MeterBar :value="c.average" :threshold="c.threshold" :label="c.title" /></div><span class="num small" style="width: 38px; text-align: right">{{ c.average }}%</span></div></td>
                <td class="num">{{ c.threshold }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="filters">
          <label class="sr-only" for="s">Search students</label>
          <input id="s" v-model="search" class="input" placeholder="Search by name, email or ID" />
          <label class="sr-only" for="c">Course</label>
          <select id="c" v-model="course" class="select"><option value="all">All courses</option><option v-for="c in data.courses" :key="c.id" :value="c.id">{{ c.code }} · {{ c.title }}</option></select>
          <label class="sr-only" for="st">Status</label>
          <select id="st" v-model="status" class="select"><option value="all">All statuses</option><option value="on-track">On track</option><option value="attention">Needs attention</option><option value="completed">Completed</option></select>
          <span class="grow" /><span class="small muted">{{ rows.length }} rows</span>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Student</th><th>Course</th><th style="min-width: 150px">Overall</th><th>Mastery by topic</th><th style="min-width: 240px">Upcoming tasks</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="r in rows" :key="r.student.id + (r.enrollment?.courseId || '')" class="clickable" tabindex="0" @click="open(r)" @keydown.enter="open(r)">
                <td><b>{{ r.student.name }}</b><div class="xs muted">{{ r.student.studentId }} · {{ r.student.program }}</div></td>
                <template v-if="r.enrollment">
                  <td><b>{{ r.enrollment.code }}</b><div class="xs muted">{{ r.enrollment.title }}</div></td>
                  <td><div class="row"><div class="grow"><MeterBar :value="r.enrollment.overall" :threshold="r.enrollment.threshold" :label="`${r.student.name} overall`" /></div><b class="num" style="width: 40px; text-align: right">{{ r.enrollment.overall }}%</b></div></td>
                  <td>
                    <div class="mini-bars">
                      <div v-for="t in r.enrollment.topics" :key="t.id" class="mb" :class="tone(t.mastery, r.enrollment.threshold)" :title="`${t.title}: ${t.mastery}%`"><i :style="{ height: Math.max(t.mastery, 3) + '%' }" /></div>
                    </div>
                    <div class="xs muted" style="margin-top: 3px">{{ r.enrollment.topics.map((t) => t.mastery + '%').join(' · ') }}</div>
                  </td>
                  <td>
                    <div v-for="t in r.enrollment.upcoming.slice(0, 2)" :key="t.id" class="small">{{ t.title }} <span class="muted">· {{ relDay(t.date) }}</span></div>
                    <span v-if="!r.enrollment.upcoming.length" class="small muted">None</span>
                  </td>
                  <td><span class="badge" :class="statusBadge[r.enrollment.status]">{{ ENR_STATUS[r.enrollment.status] }}</span></td>
                </template>
                <td v-else colspan="5" class="muted small">Not enrolled in any course</td>
              </tr>
              <tr v-if="!rows.length"><td colspan="6" class="empty">No students match these filters.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </LoadState>
</template>
