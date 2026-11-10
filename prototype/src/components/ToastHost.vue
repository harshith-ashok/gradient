<script setup>
import { toasts, dismiss } from '../stores/toast.js'
</script>

<template>
  <div class="toasts" aria-live="polite" role="status">
    <div v-for="t in toasts.items" :key="t.id" class="toast" :class="t.kind">
      <span>{{ t.message }}</span>
      <button type="button" aria-label="Dismiss" @click="dismiss(t.id)">×</button>
    </div>
  </div>
</template>
