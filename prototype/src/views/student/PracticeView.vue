<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync } from '../../lib/useAsync.js'
import { STATUS_LABEL } from '../../lib/format.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'

const router = useRouter()
const { data, loading, error } = useAsync(() => api.student.practiceOptions())
const query = ref('')
const tone = { new: '', learning: 'info', review: 'warn', mastered: 'ok' }

const groups = computed(() => {
  const q = query.value.toLowerCase().replace(/^quiz me on\s*/, '').trim()
  return (data.value || []).map((c) => ({ ...c, subtopics: c.subtopics.filter((s) => !q || `${s.title} ${s.topic}`.toLowerCase().includes(q)) })).filter((c) => c.subtopics.length)
})
const first = computed(() => groups.value[0] && { course: groups.value[0].courseId, sub: groups.value[0].subtopics[0].id })

const start = (courseId, sid) => router.push({ path: `/student/courses/${courseId}/quiz`, query: { kind: 'ondemand', subtopicId: sid, n: Date.now() } })
const go = () => first.value && start(first.value.course, first.value.sub)
</script>

<template>
  <PageHeader eyebrow="On-demand practice" title="Quiz me on…" lede="Pick any sub-topic from your courses for a quick quiz. Results update your mastery and, if you score below the pass mark, your plan." />
  <LoadState :loading="loading" :error="error">
    <template v-if="data">
      <div v-if="!data.length" class="card empty"><h3>No courses yet</h3><p>Enrol in a course to practise its sub-topics.</p><RouterLink to="/student/courses" class="btn">Browse courses</RouterLink></div>
      <template v-else>
        <form class="card card-pad row" style="margin-bottom: 22px" @submit.prevent="go">
          <label class="sr-only" for="q">Search sub-topics</label>
          <input id="q" v-model="query" class="input" placeholder="Quiz me on… (e.g. pointers, elasticity, inheritance)" autocomplete="off" />
          <button class="btn" type="submit" :disabled="!first">Start quiz</button>
        </form>
        <div v-if="!groups.length" class="card empty">No sub-topic matches “{{ query }}”.</div>
        <div class="stack">
          <section v-for="c in groups" :key="c.courseId" class="card">
            <div class="card-head"><h3>{{ c.code }} · {{ c.title }}</h3><span class="xs muted">{{ c.subtopics.length }} sub-topics</span></div>
            <ul style="list-style: none; margin: 0; padding: 0">
              <li v-for="s in c.subtopics" :key="s.id" class="row" style="padding: 11px 22px; border-bottom: 1px solid var(--line-soft)">
                <div class="grow"><div style="font-weight: 500">{{ s.title }}</div><div class="xs muted">{{ s.topic }}</div></div>
                <span class="badge" :class="tone[s.status]">{{ STATUS_LABEL[s.status] }}</span>
                <span class="num small" style="width: 40px; text-align: right">{{ s.mastery }}%</span>
                <button class="btn sm secondary" type="button" @click="start(c.courseId, s.id)">Quiz me</button>
              </li>
            </ul>
          </section>
        </div>
      </template>
    </template>
  </LoadState>
</template>
