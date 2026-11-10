<script setup>
import Crest from '../components/Crest.vue'
</script>

<template>
  <div style="min-height: 100vh; display: grid; place-items: center; padding: 24px; text-align: center">
    <div>
      <Crest :size="52" />
      <h1 style="margin-top: 18px">Page not found</h1>
      <p class="muted">The page you are looking for does not exist or has moved.</p>
      <RouterLink to="/" class="btn">Go to home</RouterLink>
    </div>
  </div>
</template>
