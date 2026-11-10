<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync, attempt } from '../../lib/useAsync.js'
import { fmtDay, fmtTs, isToday } from '../../lib/format.js'
import { toast } from '../../stores/toast.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'
import TaskRow from '../../components/TaskRow.vue'

const route = useRoute()
const courseId = computed(() => route.params.courseId)
const { data, loading, error, reload } = useAsync(() => api.student.course(courseId.value), courseId)
const e = computed(() => data.value?.enrollment)
const busy = ref(false)

const days = computed(() => {
  if (!e.value) return []
  const map = new Map()
  for (const t of e.value.tasks) {
    if (!map.has(t.day)) map.set(t.day, [])
    map.get(t.day).push(t)
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0]).map(([day, tasks]) => {
    const done = tasks.every((t) => t.done)
    return {
      day,
      date: tasks[0].date,
      tasks,
      minutes: tasks.reduce((s, t) => s + t.minutes, 0),
      done,
      status: e.value.dayStatuses.find((d) => d.dayIndex === day) || null,
      today: isToday(tasks[0].date),
    }
  })
})

async function setMinutes(ev) {
  busy.value = true
  const res = await attempt(() => api.student.setPlanMinutes(courseId.value, Number(ev.target.value)))
  busy.value = false
  if (res) {
    toast('Plan recalculated for your new daily study time.', 'success')
    reload()
  }
}
const noticeTone = { reschedule: 'warn', recalc: 'info', info: 'navy' }
const noticeLabel = { reschedule: 'Rescheduled', recalc: 'Recalculated', info: 'Created' }
</script>

<template>
  <LoadState :loading="loading" :error="error">
    <template v-if="data && !e">
      <div class="card empty"><h3>No plan yet</h3><p>Your plan is created from the pre-test.</p><RouterLink :to="`/student/courses/${courseId}/pretest`" class="btn">Take the pre-test</RouterLink></div>
    </template>
    <template v-else-if="data">
      <PageHeader :crumbs="[{ label: 'Courses', to: '/student/courses' }, { label: data.course.code, to: `/student/courses/${courseId}` }, { label: 'Study plan' }]" eyebrow="Personalised study plan" :title="data.course.title" lede="Built from your pre-test. When a quiz comes back below the pass mark, the topic is rescheduled with remediation and the rest of the plan is recalculated.">
        <template #actions>
          <label class="row small" style="gap: 8px">
            <span class="muted">Daily study time</span>
            <select class="select" style="width: auto" :value="e.minutesPerDay" :disabled="busy" @change="setMinutes">
              <option v-for="m in [30, 45, 60, 90, 120]" :key="m" :value="m">{{ m }} minutes</option>
            </select>
          </label>
        </template>
      </PageHeader>

      <div class="grid" style="grid-template-columns: minmax(0, 1fr) 340px; align-items: start; gap: 24px">
        <div>
          <article v-for="d in days" :key="d.day" class="card day" :class="{ today: d.today }">
            <div class="day-head">
              <span class="dn">Day {{ d.day + 1 }}</span>
              <span class="small muted">{{ fmtDay(d.date) }}</span>
              <span v-if="d.today" class="badge gold plain">Today</span>
              <span class="grow" />
              <span v-if="d.status" class="badge ok">{{ d.status.message }}</span>
              <span v-else-if="d.done" class="badge ok">Completed</span>
              <span v-else class="small muted">{{ d.minutes }} min</span>
            </div>
            <div class="day-body">
              <TaskRow v-for="t in d.tasks" :key="t.id" :task="t" :course-id="courseId" />
            </div>
          </article>
        </div>

        <aside class="card" style="position: sticky; top: 16px">
          <div class="card-head"><h3>Plan updates</h3></div>
          <div class="card-body" style="padding-top: 4px; padding-bottom: 4px">
            <div v-for="n in e.notices" :key="n.id" class="notice" style="flex-direction: column; gap: 4px">
              <div class="row"><span class="badge" :class="noticeTone[n.kind]">{{ noticeLabel[n.kind] }}</span><span class="when" style="min-width: 0">{{ fmtTs(n.ts) }}</span></div>
              <div>{{ n.text }}</div>
            </div>
          </div>
        </aside>
      </div>
    </template>
  </LoadState>
</template>
