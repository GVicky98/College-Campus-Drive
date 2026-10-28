<script setup>
// Applied → Shortlisted → Interview → Selected → Offer received (+ Rejected / Withdrawn as a final step).
import { computed } from 'vue'
import { Check, X } from '@lucide/vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps({ application: { type: Object, required: true } })
const STEPS = [['applied', 'Applied'], ['shortlisted', 'Shortlisted'], ['interview', 'Interview'], ['selected', 'Selected'], ['offer_received', 'Offer received']]

const steps = computed(() => {
  const history = props.application.history || []
  const at = (s) => [...history].reverse().find((h) => h.status === s)
  const reachedIdx = Math.max(...STEPS.map(([s], i) => (at(s) ? i : -1)))
  const terminal = ['rejected', 'withdrawn'].includes(props.application.status)
  const list = STEPS.slice(0, terminal ? reachedIdx + 1 : STEPS.length).map(([s, label], i) => ({
    status: s, label, entry: at(s), done: i <= reachedIdx, failed: false,
    current: !terminal && s === props.application.status,
  }))
  if (terminal) {
    const s = props.application.status
    list.push({ status: s, label: s === 'rejected' ? 'Not taken forward' : 'Withdrawn', entry: at(s), done: true, failed: true, current: true })
  }
  return list
})
</script>

<template>
  <ol class="relative space-y-5">
    <li v-for="(s, i) in steps" :key="s.status" class="relative flex gap-3">
      <span v-if="i < steps.length - 1" class="absolute top-7 left-3.5 h-[calc(100%-4px)] w-px" :class="s.done ? 'bg-brand-500' : 'bg-line'" />
      <span class="z-10 flex size-7 shrink-0 items-center justify-center rounded-full border-2"
        :class="s.failed ? 'border-red-600 bg-red-600 text-white' : s.done ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-white text-slate-400'">
        <X v-if="s.failed" class="size-3.5" /><Check v-else-if="s.done" class="size-3.5" /><span v-else class="text-xs">{{ i + 1 }}</span>
      </span>
      <div class="min-w-0 pt-0.5">
        <p class="text-sm font-medium" :class="!s.done && 'text-muted'">{{ s.label }}<span v-if="s.current" class="font-normal text-muted"> · current</span></p>
        <p v-if="s.entry" class="text-xs text-muted">{{ formatDateTime(s.entry.at) }} · {{ s.entry.by }}<span v-if="s.entry.note"> — {{ s.entry.note }}</span></p>
        <p v-else-if="!s.done" class="text-xs text-slate-400">Pending</p>
      </div>
    </li>
  </ol>
</template>
