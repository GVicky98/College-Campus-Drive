<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Bookmark, BookmarkCheck } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import EligibilityReasons from '@/components/EligibilityReasons.vue'
import ApplyDialog from '@/components/ApplyDialog.vue'
import { jobsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { daysUntil, formatDate, formatDateTime, formatPackage } from '@/utils/format'

const route = useRoute()
const toast = useToast()
const { deptCode } = useReference()
const { data: v, loading, error, reload } = useAsync(() => jobsApi.get(route.params.jobId))
const applyOpen = ref(false)

const isOpen = computed(() => v.value && v.value.job.status === 'published' && daysUntil(v.value.job.deadline) > 0)
const canApply = computed(() => isOpen.value && !v.value.applicationStatus && v.value.eligibility?.state === 'eligible')

async function toggleSave() {
  try {
    v.value.saved = (await jobsApi.toggleSave(v.value.job.id)).saved
    toast.success(v.value.saved ? 'Saved to your list' : 'Removed from saved')
  } catch (e) { toast.error(e.message) }
}
</script>

<template>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!v" :rows="10" @retry="reload">
    <template v-if="v">
      <PageHeader :title="v.job.title" :crumbs="[{ label: 'Jobs', to: '/student/jobs' }, { label: v.job.title }]">
        <template #subtitle>
          <span class="flex flex-wrap items-center gap-2">
            <CompanyLogo :company="v.company" size="sm" /> {{ v.company.name }}
            <StatusChip kind="tier" :value="v.company.tier" /><StatusChip kind="job" :value="v.job.status" />
          </span>
        </template>
        <template #actions>
          <button class="btn btn-secondary" @click="toggleSave">
            <component :is="v.saved ? BookmarkCheck : Bookmark" class="size-4" /> {{ v.saved ? 'Saved' : 'Save' }}
          </button>
          <button class="btn btn-primary" :disabled="!canApply" @click="applyOpen = true">
            {{ v.applicationStatus ? 'Applied' : isOpen ? 'Apply now' : 'Applications closed' }}
          </button>
        </template>
      </PageHeader>

      <div class="grid gap-6 lg:grid-cols-3">
        <div class="space-y-6 lg:col-span-2">
          <SectionCard title="About the role">
            <p class="text-sm whitespace-pre-line text-slate-700">{{ v.job.description || 'No description provided.' }}</p>
            <template v-if="v.job.responsibilities.length">
              <h3 class="mt-4 mb-2 text-sm">Responsibilities</h3>
              <ul class="list-disc space-y-1 pl-5 text-sm text-slate-700"><li v-for="r in v.job.responsibilities" :key="r">{{ r }}</li></ul>
            </template>
            <div v-if="v.job.skills.length" class="mt-4 flex flex-wrap gap-1.5">
              <span v-for="s in v.job.skills" :key="s" class="rounded bg-slate-100 px-2 py-0.5 text-xs">{{ s }}</span>
            </div>
          </SectionCard>
          <SectionCard title="Eligibility requirements">
            <dl class="grid gap-4 text-sm sm:grid-cols-2">
              <div><dt class="text-xs text-muted">Minimum CGPA</dt><dd class="font-medium">{{ v.job.eligibility.minCgpa }}</dd></div>
              <div><dt class="text-xs text-muted">Active arrears allowed</dt><dd class="font-medium">{{ v.job.eligibility.maxActiveArrears }}</dd></div>
              <div><dt class="text-xs text-muted">Arrear history allowed</dt><dd class="font-medium">{{ v.job.eligibility.maxArrearHistory ?? 'No limit' }}</dd></div>
              <div><dt class="text-xs text-muted">Batches</dt><dd class="font-medium">{{ v.job.eligibility.graduationYears.join(', ') || 'All' }}</dd></div>
              <div class="sm:col-span-2"><dt class="text-xs text-muted">Departments</dt>
                <dd class="font-medium">{{ v.job.eligibility.departmentIds.map(deptCode).join(', ') || 'All departments' }}</dd></div>
            </dl>
          </SectionCard>
          <SectionCard title="Hiring rounds">
            <p v-if="!v.job.rounds.length" class="text-sm text-muted">The rounds will be announced.</p>
            <ol v-else class="space-y-3">
              <li v-for="(r, i) in v.job.rounds" :key="r.id" class="flex gap-3 text-sm">
                <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700">{{ i + 1 }}</span>
                <div><p class="font-medium">{{ r.name }}</p><p class="text-xs text-muted">{{ r.mode }}<span v-if="r.date"> · {{ formatDateTime(r.date) }}</span><span v-if="r.location"> · {{ r.location }}</span></p></div>
              </li>
            </ol>
          </SectionCard>
        </div>

        <div class="space-y-6">
          <SectionCard title="Your eligibility">
            <EligibilityReasons :result="v.eligibility" />
            <div v-if="v.applicationStatus" class="mt-4 flex items-center justify-between rounded-xl bg-slate-50 p-3 text-sm">
              <span>Your application: <StatusChip kind="application" :value="v.applicationStatus" /></span>
              <RouterLink :to="`/student/applications/${v.applicationId}`" class="link">View</RouterLink>
            </div>
            <p v-if="!isOpen" class="alert alert-warning mt-4">This job is not accepting applications.</p>
          </SectionCard>
          <SectionCard title="Key details">
            <dl class="space-y-3 text-sm">
              <div class="flex justify-between gap-3"><dt class="text-muted">Package</dt><dd class="font-medium">{{ formatPackage(v.job.ctcLpa, v.job.stipendPerMonth) }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Type</dt><dd>{{ v.job.type }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Location</dt><dd>{{ v.job.location || '—' }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Domain</dt><dd>{{ v.job.domain }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Applications open</dt><dd>{{ formatDate(v.job.openDate) }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Deadline</dt><dd>{{ formatDateTime(v.job.deadline) }}</dd></div>
              <div v-if="v.job.driveDate" class="flex justify-between gap-3"><dt class="text-muted">Drive date</dt><dd>{{ formatDateTime(v.job.driveDate) }}</dd></div>
            </dl>
          </SectionCard>
        </div>
      </div>
      <ApplyDialog v-model:open="applyOpen" :view="v" @applied="reload" />
    </template>
  </AsyncBlock>
</template>
