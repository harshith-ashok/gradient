<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync, attempt } from '../../lib/useAsync.js'
import { STATUS_LABEL } from '../../lib/format.js'
import { toast } from '../../stores/toast.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'
import MeterBar from '../../components/MeterBar.vue'
import FlashcardDeck from '../../components/FlashcardDeck.vue'

const route = useRoute()
const router = useRouter()
const courseId = computed(() => String(route.params.courseId))
const subId = computed(() => String(route.params.subtopicId))
const { data, loading, error, reload } = useAsync(() => api.student.subtopic(courseId.value, subId.value), () => [courseId.value, subId.value])
const tab = ref('summary')
watch(() => route.query.tab, (t) => { tab.value = ['summary', 'cards', 'help'].includes(t) ? t : 'summary' }, { immediate: true })
const busy = ref(false)

const pendingStudy = computed(() => data.value?.tasks.find((t) => !t.done && t.type === 'study'))
const pendingHelp = computed(() => data.value?.tasks.find((t) => !t.done && t.type === 'remediation'))
const tone = { new: '', learning: 'info', review: 'warn', mastered: 'ok' }
const quizTo = computed(() => ({ path: `/student/courses/${courseId.value}/quiz`, query: { kind: 'subtopic', subtopicId: subId.value, n: Date.now() } }))

async function complete(type) {
  busy.value = true
  const res = await attempt(() => api.student.completeStudy(courseId.value, subId.value, type))
  busy.value = false
  if (!res) return
  toast(type === 'study' ? 'Marked as studied.' : 'Remediation material marked as reviewed.', 'success')
  if (res.dayStatus) toast(res.dayStatus.message, 'success', 6500)
  reload()
}
const setTab = (t) => router.replace({ query: { ...route.query, tab: t } })
</script>

<template>
  <LoadState :loading="loading" :error="error">
    <template v-if="data">
      <PageHeader :crumbs="[{ label: 'Courses', to: '/student/courses' }, { label: data.course.code, to: `/student/courses/${courseId}` }, { label: data.topic.title }]" :eyebrow="data.topic.title" :title="data.subtopic.title" :lede="data.subtopic.description">
        <template #actions>
          <RouterLink :to="quizTo" class="btn">Take the quiz</RouterLink>
        </template>
      </PageHeader>

      <div v-if="data.mastery.remediation" class="callout warn" style="margin-bottom: 20px">
        <b>This sub-topic needs review.</b> Your last quiz score was {{ data.mastery.lastScore }}%, below the {{ data.threshold }}% pass mark. Work through the
        <button class="link-btn" type="button" @click="setTab('help')">remediation material</button>, then retake the quiz.
      </div>

      <div class="grid" style="grid-template-columns: minmax(0, 1fr) 300px; align-items: start; gap: 24px">
        <div>
          <div class="tabs" role="tablist">
            <button role="tab" :aria-selected="tab === 'summary'" @click="setTab('summary')">Summary</button>
            <button role="tab" :aria-selected="tab === 'cards'" @click="setTab('cards')">Flashcards ({{ data.subtopic.flashcards.length }})</button>
            <button role="tab" :aria-selected="tab === 'help'" @click="setTab('help')">Extra help</button>
          </div>

          <div v-if="tab === 'summary'" class="card card-pad">
            <p v-for="(p, i) in data.subtopic.summary" :key="i" style="font-size: 16px; line-height: 1.7">{{ p }}</p>
            <h4 style="margin: 22px 0 10px">Key points</h4>
            <ul style="margin: 0; padding-left: 20px; line-height: 1.8"><li v-for="p in data.subtopic.points" :key="p">{{ p }}</li></ul>
            <hr class="divider" />
            <div class="row wrap">
              <button v-if="pendingStudy" class="btn gold" type="button" :disabled="busy" @click="complete('study')">Mark as studied</button>
              <span v-else-if="data.mastery.studied" class="badge ok">Studied</span>
              <button class="btn secondary" type="button" @click="setTab('cards')">Practise with flashcards</button>
            </div>
          </div>

          <div v-else-if="tab === 'cards'" class="card card-pad"><FlashcardDeck :cards="data.subtopic.flashcards" /></div>

          <div v-else class="card card-pad stack">
            <div v-if="!data.mastery.remediation && !pendingHelp" class="callout">No remediation is scheduled. This material is here if you want another way to approach the idea.</div>
            <div>
              <h3>A different way to think about it</h3>
              <p style="margin-top: 8px; font-size: 16px; line-height: 1.7">{{ data.subtopic.remediation.explanation }}</p>
            </div>
            <div>
              <h3>Try this</h3>
              <ol style="padding-left: 20px; line-height: 1.8"><li v-for="s in data.subtopic.remediation.steps" :key="s">{{ s }}</li></ol>
            </div>
            <div class="row wrap">
              <button v-if="pendingHelp" class="btn gold" type="button" :disabled="busy" @click="complete('remediation')">Mark remediation as reviewed</button>
              <RouterLink :to="quizTo" class="btn secondary">Retake the quiz</RouterLink>
            </div>
          </div>
        </div>

        <aside class="stack">
          <div class="card card-pad">
            <div class="row between"><h4>Mastery</h4><span class="badge" :class="tone[data.mastery.status]">{{ STATUS_LABEL[data.mastery.status] }}</span></div>
            <div class="big-num num" style="margin: 10px 0 8px; font-size: 40px">{{ data.mastery.value }}%</div>
            <MeterBar :value="data.mastery.value" :threshold="data.threshold" label="Mastery" />
            <p class="xs muted" style="margin: 10px 0 0">Pass mark {{ data.threshold }}% · {{ data.mastery.attempts }} quiz attempt{{ data.mastery.attempts === 1 ? '' : 's' }}{{ data.mastery.lastScore != null ? ` · last score ${data.mastery.lastScore}%` : '' }}</p>
          </div>
          <div class="card card-pad">
            <h4 style="margin-bottom: 8px">In your plan</h4>
            <div v-for="t in data.tasks" :key="t.id" class="task" :class="{ done: t.done }" style="padding: 8px 0">
              <span class="tick">{{ t.done ? '✓' : '' }}</span>
              <div class="grow"><div class="t-title" style="font-size: 13.5px">{{ t.title }}</div><div class="t-meta">{{ t.done ? t.result : 'Day ' + (t.day + 1) }}</div></div>
            </div>
            <p v-if="!data.tasks.length" class="small muted" style="margin: 0">No tasks planned for this sub-topic.</p>
          </div>
          <div class="row between small">
            <RouterLink v-if="data.prev" :to="`/student/courses/${courseId}/subtopics/${data.prev.id}`">← {{ data.prev.title }}</RouterLink><span v-else />
            <RouterLink v-if="data.next" :to="`/student/courses/${courseId}/subtopics/${data.next.id}`">{{ data.next.title }} →</RouterLink>
          </div>
        </aside>
      </div>
    </template>
  </LoadState>
</template>
