<script setup>
defineProps({ loading: Boolean, error: String })
</script>

<template>
  <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
  <div v-else-if="error" class="callout bad">{{ error }}</div>
  <slot v-else />
</template>
