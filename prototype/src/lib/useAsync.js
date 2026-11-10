import { ref, watch } from 'vue'
import { toast } from '../stores/toast.js'
import { session } from '../stores/session.js'
import router from '../router/index.js'

/** Load data from the mock backend with loading/error state. Reloads when `source` changes. */
export function useAsync(fn, source) {
  const data = ref(null)
  const loading = ref(true)
  const error = ref('')
  let seq = 0
  async function run(silent = false) {
    const mine = ++seq
    loading.value = !silent
    error.value = ''
    try {
      const res = await fn()
      if (mine === seq) data.value = res
    } catch (e) {
      if (mine !== seq) return
      error.value = e.message
      if (e.status === 401) {
        session.user = null
        router.push('/login')
      }
    } finally {
      if (mine === seq) loading.value = false
    }
  }
  if (source) watch(source, () => run(), { immediate: true })
  else run()
  // reload() refreshes in the background without flashing the spinner
  return { data, loading, error, reload: () => run(true) }
}

/** Run an action and surface errors as a toast. Returns undefined on failure. */
export async function attempt(fn, errorPrefix = '') {
  try {
    return await fn()
  } catch (e) {
    toast(`${errorPrefix}${e.message}`, 'error')
    return undefined
  }
}
