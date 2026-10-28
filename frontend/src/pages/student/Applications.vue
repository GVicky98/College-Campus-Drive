<script setup>
import { reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import { applicationsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { formatDate, formatNextAction, timeAgo } from '@/utils/format'

const router = useRouter()
const f = reactive({ q: '', status: '', page: 1 })
watch(() => [f.q, f.status], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => applicationsApi.mine({ ...f, pageSize: 10 }), { watch: f })

const columns = [
  { key: 'company', label: 'Company' },
  { key: 'job', label: 'Job title' },
  { key: 'applied', label: 'Applied', hide: 'md' },
  { key: 'status', label: 'Status' },
  { key: 'next', label: 'Next step', hide: 'lg' },
  { key: 'updated', label: 'Last updated', hide: 'sm' },
  { key: 'view', label: '', align: 'right' },
]
const statuses = ['applied', 'shortlisted', 'interview', 'selected', 'offer_received', 'rejected', 'withdrawn']
  .map((s) => ({ value: s, label: s.replace('_', ' ').replace(/^\w/, (c) => c.toUpperCase()) }))
</script>

<template>
  <PageHeader title="My Applications" subtitle="Every job you have applied to and where it stands.">
    <template #actions><RouterLink to="/student/jobs" class="btn btn-secondary">Browse jobs</RouterLink></template>
  </PageHeader>
  <DataTable :columns="columns" :rows="data?.items || []" :row-key="(r) => r.application.id" :loading="loading" :error="error"
    :total="data?.total" :page="f.page" :page-size="10" clickable empty-title="No applications yet"
    empty-message="When you apply to a job it shows up here." @page="f.page = $event" @retry="reload"
    @row-click="(r) => router.push(`/student/applications/${r.application.id}`)">
    <template #toolbar>
      <div class="flex flex-wrap gap-3">
        <SearchInput v-model="f.q" placeholder="Search company or job" />
        <SelectFilter v-model="f.status" label="Status" :options="statuses" />
      </div>
    </template>
    <template #cell-company="{ row }">
      <span class="flex items-center gap-2"><CompanyLogo :company="row.company" size="sm" />{{ row.company.name }}</span>
    </template>
    <template #cell-job="{ row }"><span class="font-medium">{{ row.job.title }}</span></template>
    <template #cell-applied="{ row }">{{ formatDate(row.application.appliedAt) }}</template>
    <template #cell-status="{ row }"><StatusChip kind="application" :value="row.application.status" /></template>
    <template #cell-next="{ row }"><span class="text-muted">{{ formatNextAction(row.nextAction) }}</span></template>
    <template #cell-updated="{ row }"><span class="text-muted">{{ timeAgo(row.application.updatedAt) }}</span></template>
    <template #cell-view="{ row }"><RouterLink :to="`/student/applications/${row.application.id}`" class="link text-xs" @click.stop>View details</RouterLink></template>
    <template #empty><RouterLink to="/student/jobs" class="btn btn-primary">Find jobs</RouterLink></template>
  </DataTable>
</template>
