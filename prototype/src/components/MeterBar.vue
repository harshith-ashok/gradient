<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: Number, default: 0 }, threshold: { type: Number, default: null }, thin: Boolean, label: { type: String, default: 'Progress' } })
const tone = computed(() => (props.threshold == null ? '' : props.value >= props.threshold ? 'ok' : props.value >= props.threshold - 25 ? 'warn' : 'bad'))
</script>

<template>
  <div class="meter" :class="[tone, { thin }]" role="progressbar" :aria-valuenow="value" aria-valuemin="0" aria-valuemax="100" :aria-label="label">
    <i :style="{ width: Math.min(100, Math.max(0, value)) + '%' }" />
    <span v-if="threshold != null" class="mark" :style="{ left: threshold + '%' }" :title="`Pass mark ${threshold}%`" />
  </div>
</template>
