<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '../../backend/index.js'
import { useAsync, attempt } from '../../lib/useAsync.js'
import { toast } from '../../stores/toast.js'
import PageHeader from '../../components/PageHeader.vue'
import LoadState from '../../components/LoadState.vue'

const { data, loading, error } = useAsync(() => api.admin.settings())
const globalT = ref(70)
const rows = ref([])
const saving = ref(false)
let snapshot = ''

function load(d) {
  globalT.value = d.globalThreshold
  rows.value = d.courses.map((c) => ({ ...c, useOverride: c.override !== null, value: c.override ?? d.globalThreshold }))
  snapshot = JSON.stringify([globalT.value, rows.value.map((r) => [r.id, r.useOverride ? r.value : null])])
}
watch(data, (d) => d && load(d), { immediate: true })

const current = computed(() => JSON.stringify([globalT.value, rows.value.map((r) => [r.id, r.useOverride ? r.value : null])]))
const dirty = computed(() => current.value !== snapshot)
const effective = (r) => (r.useOverride ? r.value : globalT.value)

async function save() {
  saving.value = true
  const perCourse = Object.fromEntries(rows.value.filter((r) => r.useOverride).map((r) => [r.id, Number(r.value)]))
  const res = await attempt(() => api.admin.saveSettings({ globalThreshold: Number(globalT.value), perCourse }))
  saving.value = false
  if (res) {
    load(res)
    toast('Pass mark settings saved. They apply to every quiz from now on.', 'success')
  }
}
</script>

<template>
  <PageHeader eyebrow="Management" title="Quiz pass mark" lede="The pass mark decides when a quiz result is good enough. A lower score reschedules the topic, adds remediation material and recalculates the student’s plan." />
  <LoadState :loading="loading" :error="error">
    <div v-if="data" class="stack" style="max-width: 860px">
      <div class="card card-pad">
        <h2>Global pass mark</h2>
        <p class="muted small">Used for every course that does not have its own setting.</p>
        <div class="row" style="gap: 22px; margin-top: 12px">
          <div class="big-num num" style="width: 120px">{{ globalT }}%</div>
          <div class="grow">
            <label class="sr-only" for="g">Global pass mark</label>
            <input id="g" v-model.number="globalT" class="range" type="range" min="40" max="100" step="5" />
            <div class="row between xs muted"><span>40%</span><span>100%</span></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head"><h2>Per-course overrides</h2></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Course</th><th>Status</th><th>Override</th><th style="width: 140px">Pass mark</th><th class="num">Applies</th></tr></thead>
            <tbody>
              <tr v-for="r in rows" :key="r.id">
                <td><b>{{ r.code }}</b> · {{ r.title }}</td>
                <td><span class="badge" :class="r.status === 'published' ? 'ok' : 'warn'">{{ r.status === 'published' ? 'Published' : 'Draft' }}</span></td>
                <td><label class="checkbox"><input v-model="r.useOverride" type="checkbox" :aria-label="`Override pass mark for ${r.title}`" /><span class="small">Use own pass mark</span></label></td>
                <td><div class="row" style="gap: 6px"><input v-model.number="r.value" class="input" type="number" min="40" max="100" step="5" :disabled="!r.useOverride" :aria-label="`Pass mark for ${r.title}`" style="width: 84px" /><span class="muted">%</span></div></td>
                <td class="num"><b>{{ effective(r) }}%</b></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="row">
        <button class="btn gold lg" type="button" :disabled="!dirty || saving" @click="save">{{ saving ? 'Saving…' : 'Save settings' }}</button>
        <span v-if="dirty" class="badge warn">Unsaved changes</span>
      </div>
    </div>
  </LoadState>
</template>
