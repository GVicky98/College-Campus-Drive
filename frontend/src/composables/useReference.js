import { ref } from 'vue'
import { referenceApi } from '@/api'

// Dropdown options (departments, batches, companies, jobs), loaded once per page load and shared.
const data = ref(null)
let pending = null

export function useReference() {
  if (!data.value && !pending) {
    pending = referenceApi.filters().then((r) => { data.value = r }).catch(() => {}).finally(() => { pending = null })
  }
  const deptCode = (id) => data.value?.departments.find((d) => d.value === String(id))?.label || '—'
  const deptName = (id) => data.value?.departments.find((d) => d.value === String(id))?.name || '—'
  return { ref: data, deptCode, deptName, reload: () => referenceApi.filters().then((r) => { data.value = r }) }
}
