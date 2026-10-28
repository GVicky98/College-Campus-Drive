<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Briefcase, CalendarDays, Gift, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import CompanyDialog from './parts/CompanyDialog.vue'
import { companiesApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { formatDate, formatDateTime, formatPackage } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const base = useBase()
const { data: d, loading, error, reload } = useAsync(() => companiesApi.get(route.params.companyId))
const editOpen = ref(false)
const columns = [
  { key: 'job', label: 'Job' }, { key: 'status', label: 'Status' }, { key: 'package', label: 'Package', hide: 'sm' },
  { key: 'drive', label: 'Drive date', hide: 'md' }, { key: 'applicants', label: 'Applicants', align: 'right' },
  { key: 'selected', label: 'Selected', align: 'right', hide: 'sm' }, { key: 'offers', label: 'Offers', align: 'right' },
]
</script>

<template>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!d" :rows="8" @retry="reload">
    <template v-if="d">
      <PageHeader :title="d.company.name" :crumbs="[{ label: 'Companies', to: `${base}/companies` }, { label: d.company.name }]">
        <template #subtitle>
          <span class="flex flex-wrap items-center gap-2"><CompanyLogo :company="d.company" size="sm" />{{ d.company.industry }}
            <StatusChip kind="tier" :value="d.company.tier" /><StatusChip v-if="d.company.archivedAt" tone="neutral" label="Archived" /></span>
        </template>
        <template #actions>
          <button v-if="auth.can('companies.manage') && !d.company.archivedAt" class="btn btn-secondary" @click="editOpen = true">Edit company</button>
          <RouterLink v-if="auth.can('jobs.create') && !d.company.archivedAt" :to="`${base}/jobs/new?companyId=${d.company.id}`" class="btn btn-primary">Add job</RouterLink>
        </template>
      </PageHeader>
      <div class="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Jobs posted" :value="d.jobs.length" :icon="Briefcase" />
        <MetricCard label="Hiring drives" :value="d.jobs.filter((j) => j.job.status !== 'draft').length" :hint="`${d.interviews} interview round(s)`" :icon="CalendarDays" tone="purple" />
        <MetricCard label="Total applicants" :value="d.jobs.reduce((s, j) => s + j.applicants, 0)" :icon="Users" tone="slate" />
        <MetricCard label="Offers made" :value="d.jobs.reduce((s, j) => s + j.offers, 0)" :hint="`${d.acceptedOffers} accepted`" :icon="Gift" tone="green" />
      </div>
      <div class="mb-6 grid gap-6 lg:grid-cols-3">
        <SectionCard class="lg:col-span-2" title="About">
          <p class="text-sm whitespace-pre-line text-slate-700">{{ d.company.description || 'No description.' }}</p>
        </SectionCard>
        <SectionCard title="Contact">
          <dl class="space-y-2 text-sm">
            <div><dt class="text-xs text-muted">Person</dt><dd>{{ d.company.contactName || '—' }}</dd></div>
            <div><dt class="text-xs text-muted">E-mail</dt><dd><a v-if="d.company.contactEmail" :href="`mailto:${d.company.contactEmail}`" class="link">{{ d.company.contactEmail }}</a><span v-else>—</span></dd></div>
            <div><dt class="text-xs text-muted">Phone</dt><dd>{{ d.company.contactPhone || '—' }}</dd></div>
            <div><dt class="text-xs text-muted">Website</dt><dd><a :href="d.company.website" target="_blank" rel="noopener" class="link">{{ d.company.website }}</a></dd></div>
            <div><dt class="text-xs text-muted">On record since</dt><dd>{{ formatDate(d.company.createdAt) }}</dd></div>
          </dl>
        </SectionCard>
      </div>
      <DataTable :columns="columns" :rows="d.jobs" :row-key="(r) => r.job.id" empty-title="No jobs yet">
        <template #cell-job="{ row }"><RouterLink :to="`${base}/jobs/${row.job.id}`" class="font-medium hover:underline">{{ row.job.title }}</RouterLink></template>
        <template #cell-status="{ row }"><StatusChip kind="job" :value="row.job.status" /></template>
        <template #cell-package="{ row }">{{ formatPackage(row.job.ctcLpa, row.job.stipendPerMonth) }}</template>
        <template #cell-drive="{ row }">{{ formatDateTime(row.job.driveDate) }}</template>
      </DataTable>
      <CompanyDialog v-model:open="editOpen" :company="d.company" @saved="reload" />
    </template>
  </AsyncBlock>
</template>
