<script setup>
import { api } from '../../backend/index.js'
import { session } from '../../stores/session.js'
import { useAsync, attempt } from '../../lib/useAsync.js'
import { toast } from '../../stores/toast.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'

const { data, loading, error, reload } = useAsync(() => api.faculty.courses())

async function toggle(c) {
  const next = c.status === 'published' ? 'draft' : 'published'
  const res = await attempt(() => api.faculty.setStatus(c.id, next))
  if (res) {
    toast(next === 'published' ? `${c.code} is now visible to students.` : `${c.code} was unpublished.`, 'success')
    reload()
  }
}
async function remove(c) {
  if (!confirm(`Delete the draft “${c.title}”? This cannot be undone.`)) return
  const res = await attempt(() => api.faculty.removeCourse(c.id))
  if (res) {
    toast('Draft deleted.', 'success')
    reload()
  }
}
</script>

<template>
  <PageHeader eyebrow="Faculty" title="My courses" :lede="`${session.user.name} · ${session.user.department}`">
    <template #actions><RouterLink to="/faculty/upload" class="btn gold">Upload a syllabus</RouterLink></template>
  </PageHeader>
  <LoadState :loading="loading" :error="error">
    <div v-if="data && !data.length" class="card empty"><h3>No courses yet</h3><p>Upload a syllabus and the agent will draft the topics and sub-topics for you.</p><RouterLink to="/faculty/upload" class="btn">Upload a syllabus</RouterLink></div>
    <div v-else-if="data" class="card table-wrap">
      <table class="table">
        <thead><tr><th>Course</th><th>Status</th><th class="num">Topics</th><th class="num">Sub-topics</th><th class="num">Enrolled</th><th>Source</th><th></th></tr></thead>
        <tbody>
          <tr v-for="c in data" :key="c.id">
            <td><RouterLink :to="`/faculty/courses/${c.id}`" style="font-weight: 600">{{ c.code }} · {{ c.title }}</RouterLink><div class="xs muted">{{ c.department }}</div></td>
            <td><span class="badge" :class="c.status === 'published' ? 'ok' : 'warn'">{{ c.status === 'published' ? 'Published' : 'Draft' }}</span></td>
            <td class="num">{{ c.topics }}</td>
            <td class="num">{{ c.subtopics }}</td>
            <td class="num">{{ c.enrolled }}</td>
            <td class="small muted">{{ c.source?.fileName || '—' }}</td>
            <td>
              <div class="row" style="justify-content: flex-end">
                <RouterLink :to="`/faculty/courses/${c.id}`" class="btn sm secondary">Review &amp; edit</RouterLink>
                <button class="btn sm secondary" type="button" @click="toggle(c)">{{ c.status === 'published' ? 'Unpublish' : 'Publish' }}</button>
                <button v-if="c.status === 'draft' && !c.enrolled" class="btn sm danger" type="button" @click="remove(c)">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </LoadState>
</template>
