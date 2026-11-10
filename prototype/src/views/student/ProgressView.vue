<script setup>
import { ref, computed } from 'vue'
import { api } from '../../backend/index.js'
import { useAsync } from '../../lib/useAsync.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'
import EnrollmentProgress from '../../components/EnrollmentProgress.vue'

const { data, loading, error } = useAsync(() => api.student.progress())
const sel = ref(null)
const list = computed(() => data.value?.enrollments || [])
const current = computed(() => list.value.find((e) => e.courseId === sel.value) || list.value[0])
</script>

<template>
  <PageHeader eyebrow="Progress dashboard" title="My progress" lede="Mastery by topic, upcoming tasks, daily status and your full quiz history." />
  <LoadState :loading="loading" :error="error">
    <div v-if="!list.length" class="card empty"><h3>Nothing to report yet</h3><p>Progress appears after you enrol and take a pre-test.</p><RouterLink to="/student/courses" class="btn">Browse courses</RouterLink></div>
    <template v-else>
      <div v-if="list.length > 1" class="tabs" role="tablist">
        <button v-for="e in list" :key="e.courseId" role="tab" :aria-selected="current.courseId === e.courseId" @click="sel = e.courseId">{{ e.code }} · {{ e.title }}</button>
      </div>
      <EnrollmentProgress :e="current">
        <template #actions><RouterLink :to="`/student/courses/${current.courseId}/plan`" class="btn secondary">Study plan</RouterLink></template>
      </EnrollmentProgress>
    </template>
  </LoadState>
</template>
