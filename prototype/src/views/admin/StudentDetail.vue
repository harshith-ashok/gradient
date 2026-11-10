<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync } from '../../lib/useAsync.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'
import EnrollmentProgress from '../../components/EnrollmentProgress.vue'

const route = useRoute()
const id = computed(() => String(route.params.studentId))
const { data, loading, error } = useAsync(() => api.admin.student(id.value), id)
</script>

<template>
  <LoadState :loading="loading" :error="error">
    <template v-if="data">
      <PageHeader :crumbs="[{ label: 'Student progress', to: '/admin' }, { label: data.student.name }]" eyebrow="Student" :title="data.student.name" :lede="`${data.student.studentId} · ${data.student.program} · ${data.student.year} · ${data.student.email}`" />
      <div v-if="!data.enrollments.length" class="card empty"><h3>No enrolments</h3><p>This student has not enrolled in a course yet.</p></div>
      <div class="stack" style="--gap: 32px">
        <EnrollmentProgress v-for="e in data.enrollments" :key="e.enrollmentId" :e="e" readonly />
      </div>
    </template>
  </LoadState>
</template>
