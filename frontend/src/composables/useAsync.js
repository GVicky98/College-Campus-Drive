import { ref, watch, onMounted } from 'vue'

/**
 * Load data with loading / error state.
 *   const { data, loading, error, reload } = useAsync(() => jobsApi.list(filters.value), { watch: filters })
 * Older responses that arrive after a newer request are ignored.
 */
export function useAsync(loader, { immediate = true, watch: source = null, initial = null } = {}) {
  const data = ref(initial)
  const loading = ref(false)
  const error = ref(null)
  let ticket = 0

  async function reload() {
    const mine = ++ticket
    loading.value = true
    error.value = null
    try {
      const result = await loader()
      if (mine === ticket) data.value = result
      return result
    } catch (e) {
      if (mine === ticket) error.value = e
    } finally {
      if (mine === ticket) loading.value = false
    }
  }

  if (source) watch(source, reload, { deep: true })
  if (immediate) onMounted(reload)
  return { data, loading, error, reload }
}

/** A ref that follows `source` after `delay` ms of no changes (for search boxes). */
export function useDebounced(source, delay = 300) {
  const out = ref(source.value)
  let timer
  watch(source, (v) => {
    clearTimeout(timer)
    timer = setTimeout(() => { out.value = v }, delay)
  })
  return out
}
