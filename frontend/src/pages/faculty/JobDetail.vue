<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Award, ClipboardList, Gift, ListChecks, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import FunnelBars from '@/components/charts/FunnelBars.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import DocumentPreviewDialog from '@/components/DocumentPreviewDialog.vue'
import JobActionDialog from './parts/JobActionDialog.vue'
import { ACTION_INFO, canEditJob, jobActions } from './parts/jobActions'
import { jobsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { useReference } from '@/composables/useReference'
import { formatDate, formatDateTime, formatPackage } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const base = useBase()
const { deptCode } = useReference()
const { data: d, loading, error, reload } = useAsync(() => jobsApi.drive(route.params.jobId))
const job = computed(() => d.value?.view.job)
const funnel = computed(() => d.value && [
  { stage: 'Eligible students', value: d.value.eligibleStudents }, { stage: 'Applied', value: d.value.counts.applied },
  { stage: 'Shortlisted', value: d.value.counts.shortlisted }, { stage: 'Interview', value: d.value.counts.interview },
  { stage: 'Selected', value: d.value.counts.selected }, { stage: 'Offers', value: d.value.counts.offers },
])
const actionOpen = ref(false)
const action = ref('')
const previewId = ref(null)
const previewOpen = ref(false)
</script>

<template>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!d" :rows="10" @retry="reload">
    <template v-if="d">
      <PageHeader :title="job.title" :crumbs="[{ label: 'Jobs', to: `${base}/jobs` }, { label: job.title }]">
        <template #subtitle>
          <span class="flex flex-wrap items-center gap-2"><CompanyLogo :company="d.view.company" size="sm" />{{ d.view.company.name }}
            <StatusChip kind="job" :value="job.status" /><StatusChip v-if="job.archivedAt" tone="neutral" label="Archived" /></span>
        </template>
        <template #actions>
          <RouterLink v-if="auth.can('applications.review')" :to="`${base}/applications?jobId=${job.id}`" class="btn btn-secondary">View applicants</RouterLink>
          <RouterLink v-if="canEditJob(auth, job)" :to="`${base}/jobs/${job.id}/edit`" class="btn btn-secondary">Edit</RouterLink>
          <template v-if="auth.can('drives.publish')">
            <button v-for="a in jobActions(job)" :key="a" class="btn" :class="a === 'cancel' ? 'btn-danger' : a === 'publish' || a === 'reopen' ? 'btn-primary' : 'btn-secondary'"
              @click="action = a; actionOpen = true">{{ ACTION_INFO[a].label }}</button>
          </template>
        </template>
      </PageHeader>

      <div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
        <MetricCard label="Eligible students" :value="d.eligibleStudents" :icon="Users" tone="green" />
        <MetricCard label="Applicants" :value="d.counts.applied" :icon="ClipboardList" />
        <MetricCard label="Shortlisted" :value="d.counts.shortlisted" :icon="ListChecks" tone="purple" />
        <MetricCard label="Selected" :value="d.counts.selected" :icon="Award" tone="amber" />
        <MetricCard label="Offers" :value="d.counts.offers" :icon="Gift" tone="red" />
      </div>

      <div class="grid gap-6 lg:grid-cols-3">
        <div class="space-y-6 lg:col-span-2">
          <SectionCard title="Overview">
            <p class="text-sm whitespace-pre-line text-slate-700">{{ job.description }}</p>
            <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <div><dt class="text-xs text-muted">Package</dt><dd>{{ formatPackage(job.ctcLpa, job.stipendPerMonth) }}</dd></div>
              <div><dt class="text-xs text-muted">Type</dt><dd>{{ job.type }}</dd></div>
              <div><dt class="text-xs text-muted">Location</dt><dd>{{ job.location }}</dd></div>
            </dl>
            <div v-if="job.skills.length" class="mt-3 flex flex-wrap gap-1"><span v-for="s in job.skills" :key="s" class="rounded bg-slate-100 px-2 py-0.5 text-xs">{{ s }}</span></div>
          </SectionCard>
          <SectionCard title="Recruitment progress"><FunnelBars :stages="funnel" /></SectionCard>
          <SectionCard title="Interviews">
            <template #actions><RouterLink v-if="auth.can('applications.review')" :to="`${base}/interviews`" class="link text-xs">Manage</RouterLink></template>
            <p v-if="!d.interviews.length" class="text-sm text-muted">No interviews scheduled.</p>
            <ul v-else class="divide-y divide-line">
              <li v-for="i in d.interviews" :key="i.id" class="flex flex-wrap items-center gap-3 py-2.5 text-sm">
                <span class="font-medium">{{ i.round }}</span><span class="text-muted">{{ formatDateTime(i.at) }} · {{ i.candidateCount }} candidate(s)</span>
                <StatusChip class="ml-auto" kind="interview" :value="i.status" />
              </li>
            </ul>
          </SectionCard>
        </div>
        <div class="space-y-6">
          <SectionCard title="Schedule & hiring rounds">
            <dl class="space-y-2 text-sm">
              <div class="flex justify-between gap-3"><dt class="text-muted">Opens</dt><dd>{{ formatDate(job.openDate) }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Deadline</dt><dd>{{ formatDateTime(job.deadline) }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Drive</dt><dd>{{ formatDateTime(job.driveDate) }}</dd></div>
            </dl>
            <ol class="mt-4 space-y-2">
              <li v-for="(r, i) in job.rounds" :key="r.id" class="text-sm"><span class="font-medium">{{ i + 1 }}. {{ r.name }}</span>
                <span class="block text-xs text-muted">{{ r.mode }}<span v-if="r.date"> · {{ formatDateTime(r.date) }}</span><span v-if="r.location"> · {{ r.location }}</span></span></li>
            </ol>
          </SectionCard>
          <SectionCard title="Eligibility criteria">
            <dl class="space-y-2 text-sm">
              <div class="flex justify-between gap-3"><dt class="text-muted">Min CGPA</dt><dd>{{ job.eligibility.minCgpa }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Active arrears</dt><dd>≤ {{ job.eligibility.maxActiveArrears }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Arrear history</dt><dd>{{ job.eligibility.maxArrearHistory ?? 'No limit' }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Batches</dt><dd>{{ job.eligibility.graduationYears.join(', ') || 'All' }}</dd></div>
              <div><dt class="text-muted">Departments</dt><dd>{{ job.eligibility.departmentIds.map(deptCode).join(', ') || 'All' }}</dd></div>
            </dl>
          </SectionCard>
          <SectionCard title="Documents">
            <template #actions><RouterLink :to="`${base}/documents`" class="link text-xs">Library</RouterLink></template>
            <p v-if="!d.documents.length" class="text-sm text-muted">No circulars or brochures for this drive.</p>
            <ul v-else class="space-y-2">
              <li v-for="doc in d.documents" :key="doc.id" class="flex items-center gap-2 text-sm">
                <button class="link min-w-0 flex-1 truncate text-left" @click="previewId = doc.id; previewOpen = true">{{ doc.title }}</button>
                <StatusChip kind="processing" :value="doc.processing" />
              </li>
            </ul>
          </SectionCard>
        </div>
      </div>
      <JobActionDialog v-model:open="actionOpen" :job="job" :action="action" @done="reload" />
      <DocumentPreviewDialog v-model:open="previewOpen" :doc-id="previewId" />
    </template>
  </AsyncBlock>
</template>
