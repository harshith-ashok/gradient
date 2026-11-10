<script setup>
defineProps({ title: String, lede: String, eyebrow: String, crumbs: { type: Array, default: () => [] } })
</script>

<template>
  <div class="page-head">
    <div v-if="crumbs.length" class="crumbs">
      <template v-for="(c, i) in crumbs" :key="i">
        <RouterLink v-if="c.to" :to="c.to">{{ c.label }}</RouterLink>
        <span v-else>{{ c.label }}</span>
        <span v-if="i < crumbs.length - 1" class="sep">/</span>
      </template>
    </div>
    <div class="title-row">
      <div>
        <div v-if="eyebrow" class="eyebrow">{{ eyebrow }}</div>
        <h1>{{ title }}</h1>
        <p v-if="lede" class="lede">{{ lede }}</p>
      </div>
      <div class="row wrap"><slot name="actions" /></div>
    </div>
  </div>
</template>
