<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import QuizSession from '../../components/QuizSession.vue'

const props = defineProps({ pretest: Boolean })
const route = useRoute()
const q = computed(() => route.query)
// Re-key on the route so opening a different quiz starts a fresh session.
const key = computed(() => `${route.params.courseId}|${props.pretest}|${q.value.kind}|${q.value.topicId}|${q.value.subtopicId}|${route.query.n || ''}`)
</script>

<template>
  <QuizSession
    :key="key"
    :course-id="String(route.params.courseId)"
    :kind="pretest ? 'pretest' : String(q.kind || 'subtopic')"
    :topic-id="q.topicId ? String(q.topicId) : undefined"
    :subtopic-id="q.subtopicId ? String(q.subtopicId) : undefined"
  />
</template>
