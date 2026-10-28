<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { GraduationCap, LogOut, Menu, Search, Settings, X } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { NAV, TOP_SEARCH } from './nav'
import NotificationBell from '@/components/NotificationBell.vue'
import Avatar from '@/components/ui/Avatar.vue'
import RequirePerm from '@/components/RequirePerm.vue'
import { usePublicSettings } from '@/composables/usePublicSettings'
import { useIdleLogout } from '@/composables/useIdleLogout'
import { toast } from '@/composables/toast'
import { ROLE_LABEL } from '@/utils/format'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const drawerOpen = ref(false)
const menuOpen = ref(false)
const query = ref('')

const items = computed(() => (NAV[auth.role] || []).filter((i) => !i.perm || auth.can(i.perm)))
// The active item is the one with the longest path that prefixes the current URL.
const active = computed(() =>
  items.value.filter((i) => route.path === i.to || route.path.startsWith(i.to + '/')).sort((a, b) => b.to.length - a.to.length)[0],
)
const title = computed(() => active.value?.label || 'Campus Assistant')
const search = computed(() => TOP_SEARCH[auth.role])
const workspace = computed(() => ({ student: 'Student', faculty: 'Placement', admin: 'Admin' })[auth.role])

watch(() => route.fullPath, () => { drawerOpen.value = false; menuOpen.value = false })

function submitSearch() {
  router.push({ path: search.value.to, query: query.value.trim() ? { q: query.value.trim() } : {} })
}
async function logout() {
  await auth.logout()
  router.replace('/login')
}

const { settings } = usePublicSettings()
useIdleLogout(() => settings.value.sessionTimeoutMinutes, async () => {
  await logout()
  toast('You were signed out after a period of inactivity.', 'info')
})
</script>

<template>
  <div class="min-h-screen lg:pl-68">
    <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-white focus:p-2">
      Skip to main content
    </a>

    <!-- Sidebar (fixed on large screens, a drawer below) -->
    <div v-if="drawerOpen" class="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" @click="drawerOpen = false" />
    <aside class="fixed inset-y-0 left-0 z-40 flex w-68 flex-col bg-navy-800 text-white transition-transform lg:translate-x-0"
      :class="drawerOpen ? 'translate-x-0' : '-translate-x-full'">
      <div class="flex items-center gap-3 px-5 py-5">
        <div class="flex size-9 items-center justify-center rounded-xl bg-white/10"><GraduationCap class="size-5" /></div>
        <div>
          <p class="font-semibold leading-tight">Campus Assistant</p>
          <p class="max-w-40 truncate text-xs text-white/60" :title="settings.collegeName">{{ settings.collegeName }}</p>
          <p class="text-[11px] text-white/45">{{ workspace }} workspace</p>
        </div>
        <button class="ml-auto rounded p-1 text-white/70 hover:bg-white/10 lg:hidden" aria-label="Close menu" @click="drawerOpen = false">
          <X class="size-5" />
        </button>
      </div>
      <nav class="flex-1 space-y-0.5 overflow-y-auto px-3 pb-4" aria-label="Main">
        <RouterLink v-for="item in items" :key="item.to" :to="item.to"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition"
          :class="active?.to === item.to ? 'bg-white/15 font-medium text-white' : 'text-white/75 hover:bg-white/10 hover:text-white'">
          <component :is="item.icon" class="size-4.5 shrink-0" />
          <span class="truncate">{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="border-t border-white/10 p-3">
        <button class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/75 hover:bg-white/10 hover:text-white" @click="logout">
          <LogOut class="size-4.5" /> Logout
        </button>
      </div>
    </aside>

    <!-- Top bar -->
    <header class="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-white/85 px-4 backdrop-blur sm:px-6">
      <button class="btn-icon lg:hidden" aria-label="Open menu" @click="drawerOpen = true"><Menu class="size-5" /></button>
      <p class="truncate text-base font-semibold">{{ title }}</p>
      <form v-if="search" class="relative ml-auto hidden w-80 md:block" role="search" @submit.prevent="submitSearch">
        <Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
        <input v-model="query" type="search" class="input bg-slate-50 pl-9" :placeholder="search.placeholder" :aria-label="search.placeholder" />
      </form>
      <div class="ml-auto flex items-center gap-1 md:ml-2">
        <NotificationBell />
        <div class="relative">
          <button class="flex items-center rounded-lg p-1 hover:bg-slate-100" aria-label="Account menu" @click="menuOpen = !menuOpen">
            <Avatar :name="auth.user?.name" size="sm" />
          </button>
          <div v-if="menuOpen" class="fixed inset-0 z-30" @click="menuOpen = false" />
          <div v-if="menuOpen" class="card absolute right-0 z-40 mt-2 w-64 p-2 shadow-lg">
            <div class="px-3 py-2">
              <p class="truncate font-medium">{{ auth.user?.name }}</p>
              <p class="truncate text-xs text-muted">{{ auth.user?.email }}</p>
              <p class="mt-1 text-xs text-muted">{{ ROLE_LABEL[auth.role] }}</p>
            </div>
            <RouterLink :to="`/${auth.role}/settings`" class="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-slate-50">
              <Settings class="size-4" /> Settings
            </RouterLink>
            <button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left hover:bg-slate-50" @click="logout">
              <LogOut class="size-4" /> Log out
            </button>
          </div>
        </div>
      </div>
    </header>

    <div v-if="settings.maintenanceBanner && settings.maintenanceMessage" role="status" class="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900 sm:px-6">
      {{ settings.maintenanceMessage }}
    </div>
    <main id="main" class="mx-auto max-w-[1360px] px-4 py-6 sm:px-6 lg:px-8">
      <RouterView v-slot="{ Component }">
        <RequirePerm><component :is="Component" :key="route.path" /></RequirePerm>
      </RouterView>
    </main>
  </div>
</template>
