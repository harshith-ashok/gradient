<script setup>
import { api } from '../../backend/index.js'
import { useAsync } from '../../lib/useAsync.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'

const { data, loading, error } = useAsync(() => api.student.catalog())
</script>

<template>
  <PageHeader eyebrow="Course catalogue" title="Choose a course" lede="Enrol in a course, take a short pre-test, and receive a study plan built around what you already know." />
  <LoadState :loading="loading" :error="error">
    <div v-if="data" class="grid auto">
      <article v-for="c in data" :key="c.id" class="card course-card" :style="{ '--accent': c.accent }">
        <div class="cc-top">
          <div class="code">{{ c.code }} · {{ c.department }}</div>
          <h3>{{ c.title }}</h3>
          <p class="small muted">{{ c.description }}</p>
          <div class="row wrap xs muted" style="margin-top: 10px; gap: 4px 14px">
            <span>{{ c.topicCount }} topics</span><span>{{ c.subtopicCount }} sub-topics</span><span>{{ c.credits }} credits</span><span>{{ c.instructor }}</span>
          </div>
        </div>
        <div class="cc-foot">
          <span v-if="c.enrollment" class="badge ok">Enrolled · {{ c.enrollment.overall }}%</span>
          <span v-else class="small muted">{{ c.level }}</span>
          <div class="row">
            <RouterLink :to="`/student/courses/${c.id}`" class="btn secondary sm">{{ c.enrollment ? 'Open' : 'View topics' }}</RouterLink>
            <RouterLink v-if="!c.enrollment" :to="`/student/courses/${c.id}/pretest`" class="btn sm">Enrol</RouterLink>
          </div>
        </div>
      </article>
    </div>
  </LoadState>
</template>
