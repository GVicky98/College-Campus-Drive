<script setup>
import { computed, ref } from 'vue'
import { CalendarDays } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import { jobsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useBase } from '@/composables/useBase'
import { daysUntil, formatDate, formatDateTime } from '@/utils/format'

const base = useBase()
const tab = ref('upcoming')
const { data, loading, error, reload } = useAsync(() => jobsApi.list({ status: 'all', pageSize: 100, sort: 'deadline' }))

// Phase and progress are worked out from the dates, for a quick visual of where each drive is.
function phase(job) {
  const now = Date.now()
  const open = new Date(job.openDate).getTime()
  const deadline = new Date(job.deadline).getTime()
  const drive = job.driveDate ? new Date(job.driveDate).getTime() : null
  if (job.status === 'cancelled') return { label: 'Cancelled', pct: 0, tone: 'error' }
  if (job.status === 'published' && now < deadline)
    return { label: 'Applications open', pct: Math.max(0, Math.min(70, (70 * (now - open)) / (deadline - open))), tone: 'success' }
  if (!drive || now < drive) return { label: 'Closed · drive pending', pct: 80, tone: 'warning' }
  if (now < drive + 7 * 86400000) return { label: 'Drive held · results pending', pct: 92, tone: 'info' }
  return { label: 'Completed', pct: 100, tone: 'neutral' }
}
const drives = computed(() => (data.value?.items || []).filter((v) => v.job.status !== 'draft').map((v) => ({ ...v, phase: phase(v.job) })))
const shown = computed(() => drives.value.filter((v) => (tab.value === 'upcoming'
  ? ['Applications open', 'Closed · drive pending'].includes(v.phase.label)
  : !['Applications open', 'Closed · drive pending'].includes(v.phase.label))))
</script>

<template>
  <PageHeader title="Hiring drives" :crumbs="[{ label: 'Jobs', to: `${base}/jobs` }, { label: 'Drives' }]" subtitle="Where each campus drive stands." />
  <Tabs v-model="tab" :tabs="[{ value: 'upcoming', label: 'Upcoming & open' }, { value: 'past', label: 'Past & closed' }]" />
  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" @retry="reload">
    <div v-if="!shown.length" class="card"><EmptyState :icon="CalendarDays" title="No drives here" /></div>
    <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <RouterLink v-for="v in shown" :key="v.job.id" :to="`${base}/jobs/${v.job.id}`" class="card block p-4 transition hover:border-brand-500">
        <div class="flex items-start gap-3">
          <CompanyLogo :company="v.company" />
          <div class="min-w-0 flex-1"><p class="text-xs text-muted">{{ v.company.name }}</p><p class="truncate font-semibold">{{ v.job.title }}</p></div>
          <StatusChip kind="job" :value="v.job.status" />
        </div>
        <dl class="mt-3 grid grid-cols-3 gap-2 text-xs">
          <div><dt class="text-muted">Drive</dt><dd class="font-medium">{{ v.job.driveDate ? formatDate(v.job.driveDate) : '—' }}
            <span v-if="v.job.driveDate && daysUntil(v.job.driveDate) > 0" class="block text-muted">in {{ daysUntil(v.job.driveDate) }}d</span></dd></div>
          <div><dt class="text-muted">Apply by</dt><dd class="font-medium">{{ formatDateTime(v.job.deadline) }}</dd></div>
          <div><dt class="text-muted">Applicants</dt><dd class="font-medium">{{ v.applicantCount }}</dd></div>
        </dl>
        <div class="mt-3 flex items-center gap-2"><StatusChip :tone="v.phase.tone" :label="v.phase.label" /></div>
        <div class="mt-2 h-1.5 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-brand-600" :style="{ width: v.phase.pct + '%' }" /></div>
      </RouterLink>
    </div>
  </AsyncBlock>
</template>
