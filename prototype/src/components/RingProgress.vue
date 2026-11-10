<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: Number, default: 0 }, size: { type: Number, default: 64 }, stroke: { type: Number, default: 6 }, tone: { type: String, default: '' } })
const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const color = computed(() => ({ ok: 'var(--ok)', warn: '#c4871f', bad: 'var(--bad)' })[props.tone] || 'var(--navy-700)')
</script>

<template>
  <span class="ring" :style="{ width: size + 'px', height: size + 'px' }" role="img" :aria-label="`${value}%`">
    <svg :width="size" :height="size">
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" stroke="#ebe6d8" :stroke-width="stroke" />
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" class="arc" :style="{ '--c': c }" :stroke="color" :stroke-width="stroke" stroke-linecap="round" :stroke-dasharray="c" :stroke-dashoffset="c * (1 - Math.min(100, Math.max(0, value)) / 100)" />
    </svg>
    <b :style="{ fontSize: size * 0.28 + 'px' }">{{ value }}%</b>
  </span>
</template>
