<script setup>
// Month grid (Sun–Sat). Up to 3 events per day, then "+N more".
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { formatTime } from '@/utils/format'

const props = defineProps({ items: { type: Array, default: () => [] } }) // interview views
const emit = defineEmits(['open'])
const cursor = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const title = computed(() => cursor.value.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }))
const key = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`

const byDay = computed(() => {
  const map = {}
  for (const v of props.items) (map[key(new Date(v.interview.at))] ||= []).push(v)
  Object.values(map).forEach((l) => l.sort((a, b) => a.interview.at.localeCompare(b.interview.at)))
  return map
})
const days = computed(() => {
  const first = new Date(cursor.value)
  const start = new Date(first)
  start.setDate(1 - first.getDay())
  const weeks = Math.ceil((first.getDay() + new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate()) / 7)
  return Array.from({ length: weeks * 7 }, (_, i) => { const d = new Date(start); d.setDate(start.getDate() + i); return d })
})
const today = key(new Date())
const move = (n) => { cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + n, 1) }
const TONE = { scheduled: 'bg-blue-100 text-blue-800', completed: 'bg-green-100 text-green-800', cancelled: 'bg-red-100 text-red-800 line-through', no_show: 'bg-amber-100 text-amber-800' }
</script>

<template>
  <div class="card overflow-hidden">
    <div class="flex items-center gap-2 border-b border-line px-4 py-3">
      <p class="font-semibold">{{ title }}</p>
      <div class="ml-auto flex items-center gap-1">
        <button class="btn-icon" aria-label="Previous month" @click="move(-1)"><ChevronLeft class="size-4" /></button>
        <button class="btn btn-secondary btn-sm" @click="cursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1)">Today</button>
        <button class="btn-icon" aria-label="Next month" @click="move(1)"><ChevronRight class="size-4" /></button>
      </div>
    </div>
    <div class="grid grid-cols-7 border-b border-line bg-slate-50 text-center text-xs font-medium text-muted">
      <div v-for="d in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="d" class="py-2">{{ d }}</div>
    </div>
    <div class="grid grid-cols-7">
      <div v-for="d in days" :key="key(d)" class="min-h-24 border-b border-r border-line p-1.5 text-xs" :class="d.getMonth() !== cursor.getMonth() && 'bg-slate-50/70 text-slate-400'">
        <span class="mb-1 inline-flex size-6 items-center justify-center rounded-full" :class="key(d) === today && 'bg-brand-600 font-semibold text-white'">{{ d.getDate() }}</span>
        <button v-for="v in (byDay[key(d)] || []).slice(0, 3)" :key="v.interview.id" class="mb-1 block w-full truncate rounded px-1.5 py-0.5 text-left"
          :class="TONE[v.interview.status]" @click="emit('open', v)">{{ formatTime(v.interview.at) }} {{ v.company.name }}</button>
        <span v-if="(byDay[key(d)] || []).length > 3" class="text-muted">+{{ byDay[key(d)].length - 3 }} more</span>
      </div>
    </div>
  </div>
</template>
