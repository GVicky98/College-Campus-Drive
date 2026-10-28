import { ref } from 'vue'
import { adminApi } from '@/api'

// College name, maintenance banner and idle timeout — loaded once and shared by every page.
const settings = ref({ collegeName: 'Campus Assistant', maintenanceBanner: false, maintenanceMessage: '', sessionTimeoutMinutes: 60 })
let loaded = false

function reload() {
  return adminApi.publicSettings().then((s) => { settings.value = s }).catch(() => {})
}

export function usePublicSettings() {
  if (!loaded) { loaded = true; reload() }
  return { settings, reload }
}
