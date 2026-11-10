<script setup>
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, onBeforeRouteLeave } from 'vue-router'
import { api } from '../../backend/index.js'
import { useAsync, attempt } from '../../lib/useAsync.js'
import { toast } from '../../stores/toast.js'
import LoadState from '../../components/LoadState.vue'

const route = useRoute()
const courseId = computed(() => String(route.params.courseId))
const { data, loading, error } = useAsync(() => api.faculty.course(courseId.value), courseId)

const course = ref(null)
const orig = ref('')
const sel = ref({ type: 'course' })
const open = reactive({})
const saving = ref(false)

watch(data, (d) => {
  if (!d) return
  course.value = JSON.parse(JSON.stringify(d))
  orig.value = JSON.stringify(d)
  sel.value = { type: 'course' }
}, { immediate: true })

const dirty = computed(() => course.value && JSON.stringify(course.value) !== orig.value)
const rid = () => 'n' + Math.random().toString(36).slice(2, 9)

const topic = computed(() => sel.value.type !== 'course' && course.value.topics.find((t) => t.id === (sel.value.type === 'topic' ? sel.value.id : sel.value.topicId)))
const sub = computed(() => sel.value.type === 'sub' && topic.value?.subtopics.find((s) => s.id === sel.value.id))
const stats = computed(() => ({ topics: course.value.topics.length, subs: course.value.topics.reduce((n, t) => n + t.subtopics.length, 0) }))

const pointsText = computed({
  get: () => (sub.value ? sub.value.points.join('\n') : ''),
  set: (v) => { sub.value.points = v.split('\n') },
})
const summaryText = computed({
  get: () => (sub.value ? sub.value.summary.join('\n\n') : ''),
  set: (v) => { sub.value.summary = v.split(/\n\s*\n/) },
})

function addTopic() {
  const t = { id: rid(), title: 'New topic', subtopics: [] }
  course.value.topics.push(t)
  open[t.id] = true
  sel.value = { type: 'topic', id: t.id }
}
function addSub(t) {
  const s = { id: rid(), title: 'New sub-topic', description: '', points: [], summary: [], flashcards: [], questions: [], remediation: { explanation: '', steps: [] }, generated: true }
  t.subtopics.push(s)
  open[t.id] = true
  sel.value = { type: 'sub', id: s.id, topicId: t.id }
}
function move(arr, i, d) {
  const j = i + d
  if (j < 0 || j >= arr.length) return
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}
function removeTopic(i) {
  const t = course.value.topics[i]
  if (t.subtopics.length && !confirm(`Remove “${t.title}” and its ${t.subtopics.length} sub-topics?`)) return
  course.value.topics.splice(i, 1)
  sel.value = { type: 'course' }
}
function removeSub(t, i) {
  if (!confirm(`Remove sub-topic “${t.subtopics[i].title}”?`)) return
  t.subtopics.splice(i, 1)
  sel.value = { type: 'topic', id: t.id }
}

async function save() {
  saving.value = true
  const c = JSON.parse(JSON.stringify(course.value))
  const res = await attempt(() => api.faculty.saveCourse(c))
  saving.value = false
  if (!res) return false
  course.value = JSON.parse(JSON.stringify(res))
  orig.value = JSON.stringify(res)
  toast('Changes saved.', 'success')
  return true
}
async function setStatus(status) {
  if (dirty.value && !(await save())) return
  const res = await attempt(() => api.faculty.setStatus(course.value.id, status))
  if (res) {
    course.value.status = status
    orig.value = JSON.stringify(course.value)
    toast(status === 'published' ? 'Course published. Students can now enrol.' : 'Course unpublished.', 'success')
  }
}

onBeforeRouteLeave(() => (!dirty.value || confirm('You have unsaved changes. Leave without saving?')))
const warn = (e) => { if (dirty.value) e.preventDefault() }
onMounted(() => window.addEventListener('beforeunload', warn))
onBeforeUnmount(() => window.removeEventListener('beforeunload', warn))
const isSel = (type, id) => sel.value.type === type && sel.value.id === id
</script>

<template>
  <LoadState :loading="loading" :error="error">
    <div v-if="course" class="editor">
      <!-- Left sidebar: topics and sub-topics -->
      <aside class="ed-side" aria-label="Course outline">
        <div class="head">
          <RouterLink to="/faculty" class="small muted">← My courses</RouterLink>
          <div class="xs muted" style="margin-top: 10px; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600">{{ course.code }}</div>
          <h3 style="margin: 2px 0 8px">{{ course.title }}</h3>
          <div class="row"><span class="badge" :class="course.status === 'published' ? 'ok' : 'warn'">{{ course.status === 'published' ? 'Published' : 'Draft' }}</span><span class="xs muted">{{ stats.topics }} topics · {{ stats.subs }} sub-topics</span></div>
        </div>
        <div class="tree">
          <div class="t-node" :class="{ sel: sel.type === 'course' }" @click="sel = { type: 'course' }"><span class="chev" /><span class="name">Course details</span></div>
          <template v-for="(t, ti) in course.topics" :key="t.id">
            <div class="t-node topic" :class="{ sel: isSel('topic', t.id) }" @click="sel = { type: 'topic', id: t.id }">
              <span class="chev" role="button" :aria-label="open[t.id] === false ? 'Expand' : 'Collapse'" @click.stop="open[t.id] = open[t.id] === false">{{ open[t.id] === false ? '▸' : '▾' }}</span>
              <span class="name">{{ t.title || 'Untitled topic' }}</span>
              <span class="acts">
                <button class="icon-btn" type="button" title="Move up" :disabled="ti === 0" @click.stop="move(course.topics, ti, -1)">↑</button>
                <button class="icon-btn" type="button" title="Move down" :disabled="ti === course.topics.length - 1" @click.stop="move(course.topics, ti, 1)">↓</button>
                <button class="icon-btn" type="button" title="Remove topic" @click.stop="removeTopic(ti)">✕</button>
              </span>
            </div>
            <template v-if="open[t.id] !== false">
              <div v-for="(s, si) in t.subtopics" :key="s.id" class="t-node sub" :class="{ sel: isSel('sub', s.id) }" @click="sel = { type: 'sub', id: s.id, topicId: t.id }">
                <span class="name">{{ s.title || 'Untitled sub-topic' }}</span>
                <span class="acts">
                  <button class="icon-btn" type="button" title="Move up" :disabled="si === 0" @click.stop="move(t.subtopics, si, -1)">↑</button>
                  <button class="icon-btn" type="button" title="Move down" :disabled="si === t.subtopics.length - 1" @click.stop="move(t.subtopics, si, 1)">↓</button>
                  <button class="icon-btn" type="button" title="Remove sub-topic" @click.stop="removeSub(t, si)">✕</button>
                </span>
              </div>
              <div class="t-node sub" style="color: var(--navy-700)" @click="addSub(t)"><span class="name">＋ Add sub-topic</span></div>
            </template>
          </template>
        </div>
        <div class="foot"><button class="btn secondary sm" type="button" style="flex: 1" @click="addTopic">＋ Add topic</button></div>
      </aside>

      <!-- Main editing pane -->
      <section>
        <div class="ed-bar">
          <span v-if="dirty" class="badge warn">Unsaved changes</span>
          <span v-else class="badge ok">All changes saved</span>
          <span class="grow" />
          <button class="btn secondary sm" type="button" :disabled="!dirty || saving" @click="save">{{ saving ? 'Saving…' : 'Save changes' }}</button>
          <button v-if="course.status === 'draft'" class="btn gold sm" type="button" @click="setStatus('published')">Publish course</button>
          <button v-else class="btn secondary sm" type="button" @click="setStatus('draft')">Unpublish</button>
        </div>

        <div class="ed-main">
          <!-- Course -->
          <div v-if="sel.type === 'course'" class="stack">
            <div><div class="eyebrow">Course</div><h1>Course details</h1></div>
            <div v-if="course.source?.fileName" class="callout">Derived from <b>{{ course.source.fileName }}</b>. Use the sidebar to review each topic and sub-topic before publishing.</div>
            <div class="card card-pad">
              <div class="form-grid">
                <div class="field"><label for="c-code">Course code</label><input id="c-code" v-model="course.code" class="input" /></div>
                <div class="field"><label for="c-cr">Credits</label><input id="c-cr" v-model.number="course.credits" class="input" type="number" min="1" /></div>
              </div>
              <div class="field"><label for="c-title">Title</label><input id="c-title" v-model="course.title" class="input" /></div>
              <div class="form-grid">
                <div class="field"><label for="c-dept">Department</label><input id="c-dept" v-model="course.department" class="input" /></div>
                <div class="field"><label for="c-level">Level</label><input id="c-level" v-model="course.level" class="input" /></div>
              </div>
              <div class="field" style="margin-bottom: 0"><label for="c-desc">Description</label><textarea id="c-desc" v-model="course.description" class="textarea" style="min-height: 90px" /></div>
            </div>
          </div>

          <!-- Topic -->
          <div v-else-if="sel.type === 'topic' && topic" class="stack">
            <div><div class="eyebrow">Topic</div><h1>Edit topic</h1></div>
            <div class="card card-pad">
              <div class="field"><label for="t-title">Topic title</label><input id="t-title" v-model="topic.title" class="input" /></div>
            </div>
            <div class="card">
              <div class="card-head"><h3>Sub-topics ({{ topic.subtopics.length }})</h3><button class="btn sm secondary" type="button" @click="addSub(topic)">＋ Add sub-topic</button></div>
              <p v-if="!topic.subtopics.length" class="empty" style="padding: 24px">No sub-topics yet.</p>
              <div v-for="s in topic.subtopics" :key="s.id" class="row" style="padding: 11px 22px; border-bottom: 1px solid var(--line-soft)">
                <button class="link-btn grow" type="button" style="text-align: left; text-decoration: none; font-weight: 500" @click="sel = { type: 'sub', id: s.id, topicId: topic.id }">{{ s.title }}</button>
                <span class="xs muted">{{ s.points.length }} key points · {{ s.questions.length }} questions</span>
              </div>
            </div>
          </div>

          <!-- Sub-topic -->
          <div v-else-if="sel.type === 'sub' && sub" class="stack">
            <div><div class="eyebrow">{{ topic.title }}</div><h1>Edit sub-topic</h1></div>
            <div class="card card-pad">
              <div class="field"><label for="s-title">Sub-topic title</label><input id="s-title" v-model="sub.title" class="input" /></div>
              <div class="field"><label for="s-desc">Short description</label><input id="s-desc" v-model="sub.description" class="input" /></div>
              <div class="field">
                <label for="s-pts">Key points <span class="muted" style="font-weight: 400">— one per line</span></label>
                <textarea id="s-pts" v-model="pointsText" class="textarea" placeholder="Term: definition&#10;Another key idea" />
                <div class="hint">Use “Term: definition” to give flashcards a proper question and answer.</div>
              </div>
              <div class="field">
                <label for="s-sum">Summary shown to students <span class="muted" style="font-weight: 400">— separate paragraphs with a blank line</span></label>
                <textarea id="s-sum" v-model="summaryText" class="textarea" style="min-height: 170px" />
              </div>
              <label class="checkbox"><input v-model="sub.generated" type="checkbox" /><span><b style="font-size: 14px">Generate flashcards, quiz questions and remediation from the key points</b><span class="hint" style="display: block">Turn off to keep the existing material as written. Regenerated content appears after you save.</span></span></label>
            </div>

            <div class="grid cols-2" style="align-items: start">
              <div class="card">
                <div class="card-head"><h3>Flashcards ({{ sub.flashcards.length }})</h3></div>
                <div class="card-body">
                  <p v-if="!sub.flashcards.length" class="small muted">None yet — add key points and save.</p>
                  <div v-for="(f, i) in sub.flashcards" :key="i" class="q-preview"><b>{{ f.front }}</b><br />{{ f.back }}</div>
                </div>
              </div>
              <div class="card">
                <div class="card-head"><h3>Quiz questions ({{ sub.questions.length }})</h3></div>
                <div class="card-body">
                  <p v-if="!sub.questions.length" class="small muted">None yet — add key points and save.</p>
                  <div v-for="q in sub.questions" :key="q.id" class="q-preview">
                    <b>{{ q.text }}</b>
                    <ul><li v-for="(o, oi) in q.options" :key="oi" :class="{ right: oi === q.answer }">{{ o }}</li></ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </LoadState>
</template>
