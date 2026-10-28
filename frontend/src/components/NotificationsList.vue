<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@lucide/vue'
import SelectFilter from './ui/SelectFilter.vue'
import StatusChip from './ui/StatusChip.vue'
import EmptyState from './ui/EmptyState.vue'
import AsyncBlock from './ui/AsyncBlock.vue'
import Tabs from './ui/Tabs.vue'
import { notificationsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { formatDateTime, timeAgo } from '@/utils/format'

const router = useRouter()
const { data, loading, error, reload } = useAsync(() => notificationsApi.list(), { initial: null })
const kind = ref('')
const show = ref('all')
const items = computed(() => (data.value || [])
  .filter((n) => !kind.value || n.kind === kind.value)
  .filter((n) => show.value === 'all' || !n.read))
const unread = computed(() => (data.value || []).filter((n) => !n.read).length)
const KINDS = ['drive', 'deadline', 'interview', 'offer', 'application', 'system'].map((k) => ({ value: k, label: k[0].toUpperCase() + k.slice(1) }))

async function markRead(n) {
  if (n.read) return
  n.read = true
  try { await notificationsApi.markRead(n.id) } catch { n.read = false }
}
async function open(n) {
  await markRead(n)
  if (n.link) router.push(n.link)
}
async function markAll() {
  await notificationsApi.markAllRead()
  reload()
}
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <Tabs v-model="show" class="mb-0 border-0" :tabs="[{ value: 'all', label: 'All' }, { value: 'unread', label: 'Unread', count: unread }]" />
      <SelectFilter v-model="kind" label="Type" :options="KINDS" />
      <button class="btn btn-secondary btn-sm ml-auto" :disabled="!unread" @click="markAll">Mark all as read</button>
    </div>
    <div class="card">
      <AsyncBlock :loading="loading" :error="error" :has-data="!!data" @retry="reload">
        <EmptyState v-if="!items.length" :icon="Bell" title="No notifications" message="You're all caught up." />
        <ul v-else class="divide-y divide-line">
          <li v-for="n in items" :key="n.id" class="flex gap-3 px-5 py-4" :class="!n.read && 'bg-brand-50/50'">
            <span class="mt-1.5 size-2 shrink-0 rounded-full" :class="n.read ? 'bg-transparent' : 'bg-brand-600'" />
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2"><p class="font-medium">{{ n.title }}</p><StatusChip kind="notification" :value="n.kind" /></div>
              <p class="text-sm text-slate-700">{{ n.body }}</p>
              <p class="mt-0.5 text-xs text-muted" :title="formatDateTime(n.at)">{{ timeAgo(n.at) }}</p>
            </div>
            <div class="flex shrink-0 flex-col gap-1 sm:flex-row sm:items-start">
              <button v-if="n.link" class="btn btn-secondary btn-sm" @click="open(n)">Open</button>
              <button v-if="!n.read" class="btn btn-ghost btn-sm" @click="markRead(n)">Mark read</button>
            </div>
          </li>
        </ul>
      </AsyncBlock>
    </div>
  </div>
</template>
