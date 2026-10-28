import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/api'
import { getAccessToken, hasSessionCookie, refreshSession, setAccessToken } from '@/api/http'

export const ROLE_HOME = { student: '/student/dashboard', faculty: '/faculty/dashboard', admin: '/admin/dashboard' }

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const permissions = ref([])
  const ready = ref(false)

  const isSignedIn = computed(() => Boolean(user.value))
  const role = computed(() => user.value?.role)
  const home = computed(() => ROLE_HOME[user.value?.role] || '/login')

  /** True when the user holds ANY of the given permissions. */
  const can = (...perms) => perms.flat().some((p) => permissions.value.includes(p))

  function apply(session) {
    user.value = session.user
    permissions.value = session.permissions || []
    if (session.accessToken) setAccessToken(session.accessToken)
  }

  /** Called once on page load: restore the session from the refresh cookie, if any. */
  async function init() {
    try {
      if (!getAccessToken() && hasSessionCookie()) await refreshSession()
      if (getAccessToken()) apply(await authApi.me())
    } catch {
      user.value = null
    } finally {
      ready.value = true
    }
  }

  async function login(identifier, password, remember) {
    apply(await authApi.login({ identifier, password, remember }))
  }

  async function reloadMe() {
    apply(await authApi.me())
  }

  async function logout() {
    try { await authApi.logout() } catch { /* always sign out locally */ }
    clear()
  }

  function clear() {
    setAccessToken(null)
    user.value = null
    permissions.value = []
  }

  return { user, permissions, ready, isSignedIn, role, home, can, init, login, reloadMe, logout, clear }
})
