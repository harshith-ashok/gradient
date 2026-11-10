<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { TASK_LABEL, taskRoute, relDay } from '../lib/format.js'

const props = defineProps({ task: Object, courseId: String, showDate: Boolean, showCourse: String, locked: Boolean })
const to = computed(() => taskRoute(props.courseId, props.task))
const kind = computed(() => ({ remediation: 'warn', retake: 'warn', 'topic-quiz': 'gold', study: 'navy' })[props.task.type] || 'info')
</script>

<template>
  <div class="task" :class="{ done: task.done }">
    <span class="tick" aria-hidden="true"><Icon v-if="task.done" name="check" :size="12" /></span>
    <div class="grow">
      <div class="t-title">{{ task.title }}</div>
      <div class="t-meta">
        <span v-if="showCourse">{{ showCourse }} · </span>
        <span v-if="showDate">{{ relDay(task.date) }} · </span>{{ task.minutes }} min
        <span v-if="task.done && task.result"> · {{ task.result }}</span>
      </div>
    </div>
    <span class="badge plain" :class="kind">{{ TASK_LABEL[task.type] }}</span>
    <RouterLink v-if="!task.done && !locked" :to="to" class="btn sm secondary">Open <Icon name="arrow" :size="13" /></RouterLink>
  </div>
</template>
