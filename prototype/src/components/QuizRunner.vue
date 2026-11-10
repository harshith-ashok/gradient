<script setup>
import { ref, computed } from 'vue'
const props = defineProps({ questions: Array, submitting: Boolean })
const emit = defineEmits(['submit'])
const i = ref(0)
const answers = ref({})
const q = computed(() => props.questions[i.value])
const last = computed(() => i.value === props.questions.length - 1)
const answered = computed(() => Object.keys(answers.value).length)
const letters = ['A', 'B', 'C', 'D', 'E']

function pick(idx) {
  answers.value = { ...answers.value, [q.value.id]: idx }
}
const finish = () => emit('submit', answers.value)
</script>

<template>
  <div class="quiz-wrap">
    <div class="q-progress">
      <span>Question {{ i + 1 }} of {{ questions.length }}</span>
      <div class="meter thin"><i :style="{ width: ((i + 1) / questions.length) * 100 + '%' }" /></div>
      <span>{{ answered }} answered</span>
    </div>
    <div class="card q-card">
      <p class="q-text">{{ q.text }}</p>
      <div role="group" aria-label="Answer options">
        <button v-for="(o, idx) in q.options" :key="idx" type="button" class="opt" :aria-pressed="answers[q.id] === idx" @click="pick(idx)">
          <span class="key">{{ letters[idx] }}</span><span>{{ o }}</span>
        </button>
      </div>
      <div class="row between" style="margin-top: 20px">
        <button class="btn secondary" type="button" :disabled="i === 0" @click="i--">Back</button>
        <button v-if="!last" class="btn" type="button" :disabled="answers[q.id] === undefined" @click="i++">Next question</button>
        <button v-else class="btn gold" type="button" :disabled="submitting || answers[q.id] === undefined" @click="finish">
          {{ submitting ? 'Submitting…' : 'Submit answers' }}
        </button>
      </div>
      <p v-if="last && answered < questions.length" class="small muted" style="margin: 14px 0 0">
        {{ questions.length - answered }} unanswered question{{ questions.length - answered === 1 ? '' : 's' }} will be marked incorrect. Use Back to review.
      </p>
    </div>
  </div>
</template>
