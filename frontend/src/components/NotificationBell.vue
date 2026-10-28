<script setup>
// Bell with unread badge. Polls every 60 s; clicking an item marks it read and follows its link.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@lucide/vue'
import { notificationsApi } from '@/api'
import { timeAgo } from '@/utils/format'

const router = useRouter()
const items = ref([])
const open = ref(false)
const unread = computed(() => items.value.filter((n) => !n.read).length)

async function load() {
  try { items.value = await notificationsApi.list() } catch { /* the bell stays quiet on errors */ }
}
let timer
onMounted(() => { load(); timer = setInterval(load, 60000) })
onBeforeUnmount(() => clearInterval(timer))

function toggle() {
  open.value = !open.value
  if (open.value) load()
}
async function openItem(n) {
  if (!n.read) {
    n.read = true
    notificationsApi.markRead(n.id).catch(() => { n.read = false })
  }
  open.value = false
  if (n.link) router.push(n.link)
}
async function markAll() {
  items.value.forEach((n) => { n.read = true })
  await notificationsApi.markAllRead().catch(load)
}
</script>

<template>
  <div class="relative">
    <button class="btn-icon relative size-9" :aria-label="`Notifications, ${unread} unread`" @click="toggle">
      <Bell class="size-5" />
      <span v-if="unread" class="absolute top-1 right-1 flex min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
        {{ unread > 9 ? '9+' : unread }}
      </span>
    </button>
    <div v-if="open" class="fixed inset-0 z-30" @click="open = false" />
    <div v-if="open" class="card absolute right-0 z-40 mt-2 w-[22rem] max-w-[90vw] shadow-lg">
      <div class="flex items-center justify-between border-b border-line px-4 py-3">
        <p class="font-semibold">Notifications</p>
        <button v-if="unread" class="link text-xs" @click="markAll">Mark all read</button>
      </div>
      <p v-if="!items.length" class="px-4 py-8 text-center text-sm text-muted">You're all caught up</p>
      <ul v-else class="max-h-96 divide-y divide-line overflow-y-auto">
        <li v-for="n in items.slice(0, 8)" :key="n.id">
          <button class="flex w-full gap-3 px-4 py-3 text-left hover:bg-slate-50" :class="!n.read && 'bg-brand-50/60'" @click="openItem(n)">
            <span class="mt-1.5 size-2 shrink-0 rounded-full" :class="n.read ? 'bg-transparent' : 'bg-brand-600'" />
            <span class="min-w-0">
              <span class="block truncate text-sm font-medium">{{ n.title }}</span>
              <span class="line-clamp-2 text-xs text-muted">{{ n.body }}</span>
              <span class="mt-0.5 block text-[11px] text-slate-400">{{ timeAgo(n.at) }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
