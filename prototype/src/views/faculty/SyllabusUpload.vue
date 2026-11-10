<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../backend/index.js'
import { session } from '../../stores/session.js'
import { attempt } from '../../lib/useAsync.js'
import { toast } from '../../stores/toast.js'
import PageHeader from '../../components/PageHeader.vue'

const router = useRouter()
const step = ref(1)
const meta = ref({ code: '', title: '', department: session.user.department || '', credits: 3 })
const file = ref(null)
const text = ref('')
const over = ref(false)
const busy = ref(false)
const trace = ref([])
const analysis = ref(null)
const picked = ref({})
const fileInput = ref(null)

const textTypes = /\.(txt|md|markdown|csv)$/i
const canAnalyze = computed(() => meta.value.code.trim() && meta.value.title.trim() && (file.value || text.value.trim()))
const selectedIds = computed(() => Object.keys(picked.value).filter((k) => picked.value[k]))

async function takeFile(f) {
  if (!f) return
  if (f.size > 5 * 1024 * 1024) return toast('That file is over 5 MB. Please upload a smaller one.', 'error')
  file.value = { name: f.name, size: f.size }
  if (textTypes.test(f.name) || f.type.startsWith('text/')) text.value = await f.text()
  else text.value = ''
}
const onDrop = (e) => {
  over.value = false
  takeFile(e.dataTransfer.files[0])
}
async function useSample() {
  text.value = await api.faculty.sampleSyllabus()
  file.value = { name: 'Data-Structures-outline.txt', size: text.value.length }
  if (!meta.value.title) meta.value.title = 'Data Structures'
  if (!meta.value.code) meta.value.code = 'CS 210'
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
async function analyze() {
  busy.value = true
  trace.value = []
  const res = await attempt(() => api.faculty.analyzeSyllabus({ fileName: file.value?.name, text: text.value, courseTitle: meta.value.title }))
  if (!res) return (busy.value = false)
  for (const t of res.trace) {
    trace.value.push(t)
    await sleep(520)
  }
  analysis.value = res
  picked.value = Object.fromEntries(res.topics.map((t) => [t.id, true]))
  busy.value = false
  step.value = 2
}
const setAll = (v) => (picked.value = Object.fromEntries(analysis.value.topics.map((t) => [t.id, v])))

async function derive() {
  busy.value = true
  const res = await attempt(() => api.faculty.deriveSubtopics({ draftId: analysis.value.draftId, selectedIds: selectedIds.value, meta: meta.value }))
  busy.value = false
  if (!res) return
  toast(`Draft created with ${res.topics} topics and ${res.subtopics} sub-topics. Review them below.`, 'success', 6000)
  router.push(`/faculty/courses/${res.courseId}`)
}
const conf = { high: 'ok', medium: 'info', low: 'warn' }
</script>

<template>
  <PageHeader eyebrow="Faculty" title="Upload a syllabus" lede="The agent reads your syllabus, proposes topics for you to confirm, then derives sub-topics. You can edit everything before publishing." :crumbs="[{ label: 'My courses', to: '/faculty' }, { label: 'Upload' }]" />

  <ol class="steps" style="padding: 0">
    <li :class="{ active: step === 1, done: step > 1 }">Upload syllabus</li>
    <li :class="{ active: step === 2, done: step > 2 }">Select topics</li>
    <li :class="{ active: step === 3 }">Review sub-topics</li>
  </ol>

  <!-- Step 1 -->
  <div v-if="step === 1" class="grid" style="grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; gap: 24px">
    <div class="card card-pad">
      <h2 style="margin-bottom: 14px">Course details</h2>
      <div class="form-grid">
        <div class="field"><label for="code">Course code</label><input id="code" v-model="meta.code" class="input" placeholder="e.g. BIO 110" /></div>
        <div class="field"><label for="credits">Credits</label><input id="credits" v-model.number="meta.credits" class="input" type="number" min="1" max="12" /></div>
      </div>
      <div class="field"><label for="title">Course title</label><input id="title" v-model="meta.title" class="input" placeholder="e.g. Introduction to Cell Biology" /></div>
      <div class="field"><label for="dept">Department</label><input id="dept" v-model="meta.department" class="input" /></div>
    </div>

    <div class="card card-pad">
      <h2 style="margin-bottom: 14px">Syllabus</h2>
      <div class="drop" :class="{ over }" tabindex="0" role="button" aria-label="Choose a syllabus file" @click="fileInput.click()" @keydown.enter="fileInput.click()" @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop">
        <b>{{ file ? file.name : 'Drop a file here, or click to browse' }}</b>
        <span class="small muted">{{ file ? `${(file.size / 1024).toFixed(1)} KB` : 'PDF, Word, text or Markdown · up to 5 MB' }}</span>
        <input ref="fileInput" type="file" hidden accept=".pdf,.doc,.docx,.txt,.md,.markdown,.csv" @change="takeFile($event.target.files[0])" />
      </div>
      <p v-if="file && !text" class="callout warn small" style="margin-top: 12px">This file type cannot be read in the browser. The prototype will use a template outline; the full system extracts the text with a parsing / OCR service.</p>
      <div class="field" style="margin-top: 16px">
        <label for="paste">Or paste the syllabus text</label>
        <textarea id="paste" v-model="text" class="textarea" style="min-height: 150px; font-size: 13.5px" placeholder="Unit 1: Topic&#10;- Sub-topic one&#10;- Sub-topic two"></textarea>
        <div class="hint">Headings such as “Unit 1: …” or “1. …” become topics; bullet lines become sub-topics.</div>
      </div>
      <div class="row wrap">
        <button class="btn gold" type="button" :disabled="!canAnalyze || busy" @click="analyze">{{ busy ? 'Agent is reading…' : 'Analyse syllabus' }}</button>
        <button class="btn secondary" type="button" :disabled="busy" @click="useSample">Use a sample syllabus</button>
      </div>
    </div>

    <div v-if="trace.length" class="agent" style="grid-column: 1 / -1">
      <div v-for="(t, i) in trace" :key="i" class="ln"><span class="ok">✓</span><span class="st">{{ t.step }}</span><span class="dt">{{ t.detail }}</span></div>
      <div v-if="busy" class="ln"><span class="dt">…</span></div>
    </div>
  </div>

  <!-- Step 2 -->
  <div v-else-if="step === 2" class="stack">
    <div v-if="analysis.simulated" class="callout warn">Text could not be extracted from {{ analysis.fileName || 'this upload' }}, so a template outline is shown. Rename, remove or keep topics below.</div>
    <div class="card">
      <div class="card-head">
        <div><h2>Detected topics</h2><div class="small muted">{{ selectedIds.length }} of {{ analysis.topics.length }} selected from {{ analysis.fileName || 'pasted text' }}</div></div>
        <div class="row"><button class="btn sm secondary" type="button" @click="setAll(true)">Select all</button><button class="btn sm secondary" type="button" @click="setAll(false)">Clear</button></div>
      </div>
      <label v-for="t in analysis.topics" :key="t.id" class="topic-pick">
        <input v-model="picked[t.id]" type="checkbox" style="margin-top: 5px; width: 17px; height: 17px; accent-color: var(--navy)" />
        <div class="grow">
          <div class="row"><b style="font-family: var(--serif); font-size: 17px; color: var(--navy)">{{ t.title }}</b><span class="badge" :class="conf[t.confidence]">{{ t.confidence }} confidence</span></div>
          <ul v-if="t.subs.length"><li v-for="s in t.subs" :key="s">{{ s }}</li></ul>
          <div v-else class="small muted" style="margin-top: 4px">No sub-topics listed. The agent will derive them from the topic name.</div>
        </div>
      </label>
    </div>
    <div class="row">
      <button class="btn secondary" type="button" @click="step = 1">Back</button>
      <button class="btn gold" type="button" :disabled="!selectedIds.length || busy" @click="derive">{{ busy ? 'Deriving sub-topics…' : 'Derive sub-topics and open editor' }}</button>
    </div>
  </div>
</template>
