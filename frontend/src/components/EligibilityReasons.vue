<script setup>
import { CircleCheck, CircleHelp, CircleX } from '@lucide/vue'
import StatusChip from './ui/StatusChip.vue'
import { formatDateTime } from '@/utils/format'
defineProps({ result: { type: Object, required: true }, showTime: Boolean })
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center gap-2">
      <StatusChip kind="eligibility" :value="result.state" />
      <span class="text-sm text-slate-700">{{ result.summary }}</span>
    </div>
    <p v-if="showTime && result.evaluatedAt" class="mt-1 text-xs text-muted">Evaluated {{ formatDateTime(result.evaluatedAt) }}</p>
    <ul class="mt-3 space-y-2">
      <li v-for="c in result.checks" :key="c.key" class="flex gap-2 text-sm">
        <CircleCheck v-if="c.passed === true" class="mt-0.5 size-4 shrink-0 text-green-600" />
        <CircleX v-else-if="c.passed === false" class="mt-0.5 size-4 shrink-0 text-red-600" />
        <CircleHelp v-else class="mt-0.5 size-4 shrink-0 text-amber-600" />
        <span><span class="font-medium">{{ c.label }}</span> <span class="text-muted">— {{ c.detail }}</span></span>
      </li>
    </ul>
    <p v-if="result.exceptionGranted" class="alert alert-warning mt-3">
      Exception granted — {{ result.exceptionGranted.reason }} (approved by {{ result.exceptionGranted.approvedBy }})
    </p>
  </div>
</template>
