<script setup>
import { computed, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync } from '../../lib/useAsync.js'
import { STATUS_LABEL, relDay, ENR_STATUS } from '../../lib/format.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'
import RingProgress from '../../components/RingProgress.vue'
import MeterBar from '../../components/MeterBar.vue'

const route = useRoute()
const courseId = computed(() => route.params.courseId)
const { data, loading, error } = useAsync(() => api.student.course(courseId.value), courseId)
const closed = reactive({})
const tone = { new: '', learning: 'info', review: 'warn', mastered: 'ok' }

const enr = computed(() => data.value?.enrollment)
const subInfo = (sid) => {
  for (const t of enr.value?.topicDetail || []) {
    const s = t.subtopics.find((x) => x.id === sid)
    if (s) return s
  }
  return null
}
const topicMastery = (tid) => enr.value?.topicDetail.find((t) => t.id === tid)?.mastery
const next = computed(() => enr.value?.tasks.find((t) => !t.done))
</script>

<template>
  <LoadState :loading="loading" :error="error">
    <template v-if="data">
      <PageHeader :crumbs="[{ label: 'Courses', to: '/student/courses' }, { label: data.course.code }]" :eyebrow="`${data.course.code} · ${data.course.department}`" :title="data.course.title" :lede="data.course.description">
        <template #actions>
          <template v-if="enr">
            <RouterLink :to="`/student/courses/${courseId}/plan`" class="btn">Study plan</RouterLink>
            <RouterLink :to="`/student/practice`" class="btn secondary">Practice quiz</RouterLink>
          </template>
          <RouterLink v-else :to="`/student/courses/${courseId}/pretest`" class="btn lg">Enrol and take the pre-test</RouterLink>
        </template>
      </PageHeader>

      <div class="grid cols-3" style="margin-bottom: 28px; align-items: stretch">
        <div class="card card-pad">
          <div class="xs muted">Instructor</div>
          <div style="font-weight: 500">{{ data.course.instructor }}</div>
          <div class="xs muted" style="margin-top: 10px">Level · credits</div>
          <div>{{ data.course.level }} · {{ data.course.credits }} credits</div>
          <div class="xs muted" style="margin-top: 10px">Quiz pass mark</div>
          <div>{{ data.course.threshold }}%</div>
        </div>
        <div v-if="enr" class="card card-pad row" style="gap: 18px">
          <RingProgress :value="enr.overall" :size="84" :stroke="8" />
          <div>
            <div class="xs muted">Overall mastery</div>
            <span class="badge" :class="enr.status === 'attention' ? 'warn' : enr.status === 'completed' ? 'ok' : 'info'">{{ ENR_STATUS[enr.status] }}</span>
            <div class="small muted" style="margin-top: 6px">Pre-test {{ enr.pretestScore }}%</div>
          </div>
        </div>
        <div v-if="enr" class="card card-pad">
          <div class="xs muted">Next up</div>
          <template v-if="next">
            <div style="font-weight: 500">{{ next.title }}</div>
            <div class="small muted">{{ relDay(next.date) }} · {{ next.minutes }} min</div>
          </template>
          <div v-else>Plan complete</div>
          <RouterLink :to="`/student/courses/${courseId}/plan`" class="small">View full plan →</RouterLink>
        </div>
        <div v-else class="card card-pad callout gold" style="grid-column: span 2; border-radius: var(--radius)">
          <b>Not enrolled yet.</b>
          <p style="margin-top: 6px">Take the pre-test to unlock sub-topic summaries, flashcards, quizzes and your personalised plan.</p>
        </div>
      </div>

      <section>
        <div class="section-head" style="display: flex; justify-content: space-between; margin-bottom: 12px"><h2>Topics and sub-topics</h2></div>
        <div class="stack">
          <div v-for="(t, ti) in data.course.topics" :key="t.id" class="card">
            <button type="button" class="card-head" style="width: 100%; background: none; border: 0; border-bottom: 1px solid var(--line-soft); cursor: pointer; text-align: left" :aria-expanded="!closed[t.id]" @click="closed[t.id] = !closed[t.id]">
              <div class="grow">
                <div class="xs muted" style="letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600">Topic {{ ti + 1 }}</div>
                <h3>{{ t.title }}</h3>
              </div>
              <div v-if="enr" style="width: 140px"><MeterBar :value="topicMastery(t.id) || 0" :threshold="enr.threshold" thin :label="t.title" /></div>
              <span class="muted">{{ closed[t.id] ? '＋' : '−' }}</span>
            </button>
            <ul v-show="!closed[t.id]" style="list-style: none; margin: 0; padding: 0">
              <li v-for="s in t.subtopics" :key="s.id" class="row" style="padding: 12px 22px; border-bottom: 1px solid var(--line-soft); gap: 16px">
                <div class="grow">
                  <component :is="enr ? 'RouterLink' : 'span'" :to="`/student/courses/${courseId}/subtopics/${s.id}`" style="font-weight: 500">{{ s.title }}</component>
                  <div class="small muted">{{ s.description }}</div>
                </div>
                <template v-if="enr && subInfo(s.id)">
                  <span class="badge" :class="tone[subInfo(s.id).status]">{{ STATUS_LABEL[subInfo(s.id).status] }}</span>
                  <span class="num small" style="width: 40px; text-align: right">{{ subInfo(s.id).mastery }}%</span>
                </template>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </LoadState>
</template>
