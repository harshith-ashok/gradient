<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../backend/index.js'
import QuizRunner from './QuizRunner.vue'
import RingProgress from './RingProgress.vue'
import MeterBar from './MeterBar.vue'
import PageHeader from './PageHeader.vue'
import { relDay, taskRoute, TASK_LABEL } from '../lib/format.js'
import { toast } from '../stores/toast.js'

const props = defineProps({ courseId: String, kind: String, topicId: String, subtopicId: String })

const phase = ref('loading') // loading | intro | running | result | error
const quiz = ref(null)
const result = ref(null)
const error = ref('')
const submitting = ref(false)
const showReview = ref(false)

const isPre = computed(() => props.kind === 'pretest')
const tone = computed(() => (result.value?.passed ? 'ok' : 'bad'))
const backTo = computed(() => (props.subtopicId ? `/student/courses/${props.courseId}/subtopics/${props.subtopicId}` : `/student/courses/${props.courseId}`))

async function load() {
  phase.value = 'loading'
  result.value = null
  try {
    quiz.value = await api.student.startQuiz({ courseId: props.courseId, kind: props.kind, topicId: props.topicId, subtopicId: props.subtopicId })
    phase.value = 'intro'
  } catch (e) {
    error.value = e.message
    phase.value = 'error'
  }
}

async function submit(answers) {
  submitting.value = true
  try {
    result.value = await api.student.submitQuiz(quiz.value.quizId, answers)
    phase.value = 'result'
    if (result.value.dayStatus) toast(result.value.dayStatus.message, 'success', 6000)
  } catch (e) {
    toast(e.message, 'error')
    if (e.status === 410) load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="phase === 'loading'" class="loading"><span class="spinner" /> Preparing questions…</div>

  <div v-else-if="phase === 'error'" class="quiz-wrap">
    <div class="callout bad">{{ error }}</div>
    <p style="margin-top: 16px"><RouterLink :to="`/student/courses/${courseId}`" class="btn secondary">Back to course</RouterLink></p>
  </div>

  <!-- Intro -->
  <div v-else-if="phase === 'intro'" class="quiz-wrap">
    <PageHeader :eyebrow="isPre ? 'Diagnostic' : kind === 'topic' ? 'Topic assessment' : 'Quiz'" :title="quiz.title" :crumbs="[{ label: 'Courses', to: '/student/courses' }, { label: 'Course', to: `/student/courses/${courseId}` }, { label: quiz.title }]" />
    <div class="card card-pad stack">
      <dl class="kv">
        <dt>Scope</dt><dd>{{ quiz.scope }}</dd>
        <dt>Questions</dt><dd>{{ quiz.questions.length }} multiple choice</dd>
        <dt v-if="!isPre">Pass mark</dt><dd v-if="!isPre">{{ quiz.threshold }}%</dd>
      </dl>
      <div v-if="isPre" class="callout">
        <b>This is not graded.</b> The pre-test shows what you already know so your study plan can skip what you have mastered and spend more time where you need it. Answer honestly; guessing makes the plan less useful.
      </div>
      <div v-else class="callout gold">
        Score at least <b>{{ quiz.threshold }}%</b> to complete this step. If you score lower, the topic is rescheduled for later with extra remediation material and the rest of your plan is recalculated.
      </div>
      <div class="row">
        <button class="btn lg" type="button" @click="phase = 'running'">{{ isPre ? 'Begin pre-test' : 'Start quiz' }}</button>
        <RouterLink :to="backTo" class="btn secondary lg">Not now</RouterLink>
      </div>
    </div>
  </div>

  <!-- Running -->
  <div v-else-if="phase === 'running'">
    <div class="quiz-wrap"><PageHeader :title="quiz.title" /></div>
    <QuizRunner :questions="quiz.questions" :submitting="submitting" @submit="submit" />
  </div>

  <!-- Result -->
  <div v-else class="quiz-wrap stack">
    <PageHeader :eyebrow="isPre ? 'Pre-test complete' : 'Results'" :title="isPre ? 'Your pre-test results' : result.title" />

    <div class="card card-pad">
      <div class="score-hero">
        <RingProgress :value="result.score" :size="112" :stroke="9" :tone="isPre ? '' : tone" />
        <div class="grow">
          <template v-if="isPre">
            <h2>{{ result.correct }} of {{ result.total }} correct</h2>
            <p class="muted" style="margin: 6px 0 0">Your personalised plan covers {{ result.plan.tasks }} tasks across {{ result.plan.days }} {{ result.plan.days === 1 ? 'day' : 'days' }} at {{ result.plan.minutesPerDay }} minutes a day.</p>
          </template>
          <template v-else>
            <h2>
              <span class="badge" :class="result.passed ? 'ok' : 'bad'">{{ result.passed ? 'Passed' : 'Below pass mark' }}</span>
            </h2>
            <p class="muted" style="margin: 8px 0 0">{{ result.correct }} of {{ result.total }} correct · pass mark {{ result.threshold }}%</p>
            <div style="margin-top: 12px; max-width: 320px"><MeterBar :value="result.score" :threshold="result.threshold" label="Score" /></div>
          </template>
        </div>
      </div>
    </div>

    <div v-if="result.dayStatus" class="callout ok"><b>{{ result.dayStatus.message }}</b><br />Nice work — that closes today’s plan.</div>

    <!-- Adaptive actions -->
    <div v-if="result.actions?.failed" class="callout warn">
      <b>Your plan has been adjusted.</b>
      <ul style="margin: 8px 0 0; padding-left: 20px">
        <li v-for="a in result.actions.items" :key="a.title">{{ a.title }} — Day {{ a.day }} ({{ relDay(a.date) }})</li>
        <li>The remaining tasks were recalculated{{ result.actions.shifted ? ` (${result.actions.shifted} moved later)` : '' }}.</li>
      </ul>
    </div>

    <div class="card">
      <div class="card-head"><h3>{{ isPre ? 'Starting point by sub-topic' : 'By sub-topic' }}</h3></div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Sub-topic</th><th class="num">Correct</th><th class="num">Score</th><th class="num">{{ isPre ? 'Starting mastery' : 'Mastery' }}</th></tr></thead>
          <tbody>
            <tr v-for="s in result.bySubtopic" :key="s.subtopicId">
              <td>{{ s.title }}</td>
              <td class="num">{{ s.correct }}/{{ s.total }}</td>
              <td class="num">{{ s.score }}%</td>
              <td class="num">
                <template v-if="!isPre">{{ s.before }}% → </template><b>{{ s.after }}%</b>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="card-head">
        <h3>Question review</h3>
        <button class="btn secondary sm" type="button" @click="showReview = !showReview">{{ showReview ? 'Hide' : 'Show' }}</button>
      </div>
      <div v-if="showReview" class="card-body">
        <div v-for="(r, n) in result.review" :key="r.id" class="review-item">
          <div class="small muted">Question {{ n + 1 }} · {{ r.subtopicTitle }}</div>
          <p style="margin: 4px 0 8px; font-weight: 500">{{ r.text }}</p>
          <div v-if="!r.correct" class="ans wrong">Your answer: {{ r.chosen == null ? 'No answer' : r.options[r.chosen] }}</div><br v-if="!r.correct" />
          <div class="ans right">Correct answer: {{ r.options[r.answer] }}</div>
          <p class="small muted" style="margin: 6px 0 0">{{ r.explanation }}</p>
        </div>
      </div>
    </div>

    <div class="row wrap">
      <RouterLink v-if="isPre" :to="`/student/courses/${courseId}/plan`" class="btn lg">View my study plan</RouterLink>
      <RouterLink v-else-if="result.nextTask" :to="taskRoute(courseId, result.nextTask)" class="btn lg">Next: {{ result.nextTask.title }}</RouterLink>
      <RouterLink v-if="!isPre" :to="`/student/courses/${courseId}/plan`" class="btn secondary lg">Study plan</RouterLink>
      <RouterLink v-if="!isPre && subtopicId" :to="backTo" class="btn secondary lg">Back to sub-topic</RouterLink>
      <RouterLink v-if="!isPre" :to="`/student/courses/${courseId}`" class="btn secondary lg">Course</RouterLink>
      <span v-if="!isPre && result.nextTask" class="small muted">{{ TASK_LABEL[result.nextTask.type] }} · {{ relDay(result.nextTask.date) }}</span>
    </div>
  </div>
</template>
