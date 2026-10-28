<script setup>
import { computed } from 'vue'
import { Bookmark, BookmarkCheck, CalendarDays, MapPin } from '@lucide/vue'
import CompanyLogo from './CompanyLogo.vue'
import StatusChip from './ui/StatusChip.vue'
import { daysUntil, formatDate, formatPackage, formatShortDate } from '@/utils/format'

const props = defineProps({
  view: { type: Object, required: true }, // { job, company, eligibility?, saved?, applicationStatus?, eligibleDepartments, applicantCount? }
  compact: Boolean,
  detailTo: String,
  showSave: Boolean,
})
const emit = defineEmits(['apply', 'toggle-save'])

const job = computed(() => props.view.job)
const days = computed(() => daysUntil(job.value.deadline))
const deadlineTone = computed(() => (days.value <= 3 ? 'error' : days.value <= 7 ? 'warning' : 'neutral'))
const isOpen = computed(() => job.value.status === 'published' && days.value > 0)
const canApply = computed(() => props.view.eligibility?.state === 'eligible' && isOpen.value && !props.view.applicationStatus)
const depts = computed(() => (props.view.eligibleDepartments?.length && props.view.eligibleDepartments.length < 7 ? props.view.eligibleDepartments.join(', ') : 'All departments'))
</script>

<template>
  <article class="card flex flex-col p-4">
    <div class="flex items-start gap-3">
      <CompanyLogo :company="view.company" />
      <div class="min-w-0 flex-1">
        <p class="text-xs text-muted">{{ view.company.name }}</p>
        <RouterLink v-if="detailTo" :to="detailTo" class="block truncate font-semibold hover:underline">{{ job.title }}</RouterLink>
        <p v-else class="truncate font-semibold">{{ job.title }}</p>
      </div>
      <button v-if="showSave" class="btn-icon" :aria-label="view.saved ? 'Remove from saved' : 'Save job'" @click="emit('toggle-save', view)">
        <BookmarkCheck v-if="view.saved" class="size-4.5 text-brand-600" /><Bookmark v-else class="size-4.5" />
      </button>
    </div>

    <div class="mt-3 flex flex-wrap gap-1.5">
      <StatusChip v-if="view.eligibility" kind="eligibility" :value="view.eligibility.state" />
      <StatusChip v-else kind="job" :value="job.status" />
      <StatusChip v-if="view.applicationStatus" kind="application" :value="view.applicationStatus" />
      <StatusChip v-if="isOpen" :tone="deadlineTone" :label="days === 1 ? 'Closes in 1 day' : `Closes in ${days} days`" />
    </div>

    <div class="mt-3 space-y-1 text-sm text-slate-700">
      <p class="flex items-center gap-1.5"><MapPin class="size-3.5 text-slate-400" />{{ job.location || '—' }} · {{ job.type }}</p>
      <p class="font-medium">{{ formatPackage(job.ctcLpa, job.stipendPerMonth) }}</p>
      <p class="flex items-center gap-1.5 text-xs text-muted"><CalendarDays class="size-3.5" />Apply by {{ formatDate(job.deadline) }}<span v-if="job.driveDate"> · Drive {{ formatShortDate(job.driveDate) }}</span></p>
    </div>

    <template v-if="!compact">
      <p class="mt-3 text-xs text-muted">
        Min CGPA {{ job.eligibility.minCgpa }} · {{ job.eligibility.maxActiveArrears ? `≤ ${job.eligibility.maxActiveArrears} active arrears` : 'No active arrears' }} · {{ depts }}
      </p>
      <div v-if="job.skills.length" class="mt-2 flex flex-wrap gap-1">
        <span v-for="s in job.skills.slice(0, 4)" :key="s" class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">{{ s }}</span>
        <span v-if="job.skills.length > 4" class="text-xs text-muted">+{{ job.skills.length - 4 }}</span>
      </div>
      <p v-if="view.eligibility && view.eligibility.state !== 'eligible'" class="mt-2 text-xs text-red-700">{{ view.eligibility.summary }}</p>
      <p v-if="view.applicantCount !== undefined" class="mt-2 text-xs text-muted">{{ view.applicantCount }} applicants</p>
    </template>

    <div class="mt-auto flex gap-2 pt-4">
      <RouterLink v-if="detailTo" :to="detailTo" class="btn btn-secondary btn-sm flex-1">View details</RouterLink>
      <button v-if="view.eligibility" class="btn btn-primary btn-sm flex-1" :disabled="!canApply" @click="emit('apply', view)">
        {{ view.applicationStatus ? 'Applied' : !isOpen ? 'Closed' : 'Apply' }}
      </button>
    </div>
  </article>
</template>
