<script setup>
import { ref, computed, watch } from 'vue'
const props = defineProps({ cards: { type: Array, default: () => [] } })
const i = ref(0)
const flipped = ref(false)
const known = ref(new Set())
const card = computed(() => props.cards[i.value])
watch(() => props.cards, () => { i.value = 0; flipped.value = false; known.value = new Set() })

function go(d) {
  i.value = Math.min(props.cards.length - 1, Math.max(0, i.value + d))
  flipped.value = false
}
function mark(ok) {
  const s = new Set(known.value)
  ok ? s.add(i.value) : s.delete(i.value)
  known.value = s
  if (i.value < props.cards.length - 1) go(1)
}
</script>

<template>
  <div v-if="cards.length" class="deck">
    <div class="row between small muted" style="margin-bottom: 10px">
      <span>Card {{ i + 1 }} of {{ cards.length }}</span>
      <span>{{ known.size }} marked “got it”</span>
    </div>
    <button type="button" class="flash" :class="{ flipped }" :aria-label="flipped ? 'Show question' : 'Reveal answer'" @click="flipped = !flipped">
      <span class="inner">
        <span class="face front"><span class="tag">Prompt</span>{{ card.front }}</span>
        <span class="face back"><span class="tag">Answer</span>{{ card.back }}</span>
      </span>
    </button>
    <p class="xs faint" style="text-align: center; margin-top: 8px">Click the card to flip it.</p>
    <div class="row between" style="margin-top: 14px">
      <button class="btn secondary" type="button" :disabled="i === 0" @click="go(-1)">Previous</button>
      <div class="row">
        <button class="btn secondary" type="button" @click="mark(false)">Review again</button>
        <button class="btn" type="button" @click="mark(true)">Got it</button>
      </div>
      <button class="btn secondary" type="button" :disabled="i === cards.length - 1" @click="go(1)">Next</button>
    </div>
  </div>
  <div v-else class="empty">No flashcards for this sub-topic yet.</div>
</template>
