<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CalendarDays, Plus } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import Tabs from '@/components/ui/Tabs.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import RowMenu from '@/components/ui/RowMenu.vue'
import JobActionDialog from './parts/JobActionDialog.vue'
import { ACTION_INFO, canEditJob, jobActions } from './parts/jobActions'
import { jobsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { useReference } from '@/composables/useReference'
import { daysUntil, formatDate, formatDateTime } from '@/utils/format'

defineProps({ embedded: Boolean })
const auth = useAuthStore()
const base = useBase()
const route = useRoute()
const router = useRouter()
const reference = useReference().ref
const f = reactive({ status: 'all', q: '', companyId: route.query.companyId || '', archived: '', page: 1 })
watch(() => [f.status, f.q, f.companyId, f.archived], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => jobsApi.list({ ...f, pageSize: 10, sort: 'recent' }), { watch: f })

const columns = [
  { key: 'job', label: 'Job' }, { key: 'status', label: 'Status' }, { key: 'applicants', label: 'Applicants', align: 'right' },
  { key: 'deadline', label: 'Deadline', hide: 'md' }, { key: 'drive', label: 'Drive date', hide: 'lg' },
  { key: 'cgpa', label: 'Min CGPA', hide: 'lg' }, { key: 'menu', label: '', align: 'right' },
]
const tabs = ['all', 'draft', 'published', 'closed', 'cancelled'].map((s) => ({ value: s, label: s === 'all' ? 'All' : s[0].toUpperCase() + s.slice(1) }))
const actionOpen = ref(false)
const action = ref({ job: null, name: '' })
function runAction(job, name) { action.value = { job, name }; actionOpen.value = true }
</script>

<template>
  <PageHeader v-if="!embedded" title="Jobs & hiring drives" subtitle="Create jobs, set eligibility and run each drive's lifecycle.">
    <template #actions>
      <RouterLink :to="`${base}/drives`" class="btn btn-secondary"><CalendarDays class="size-4" /> Drive calendar</RouterLink>
      <RouterLink v-if="auth.can('jobs.create')" :to="`${base}/jobs/new`" class="btn btn-primary"><Plus class="size-4" /> New job</RouterLink>
    </template>
  </PageHeader>
  <Tabs v-model="f.status" :tabs="tabs" />
  <DataTable :columns="columns" :rows="data?.items || []" :row-key="(r) => r.job.id" :loading="loading" :error="error"
    :total="data?.total" :page="f.page" :page-size="10" clickable empty-title="No jobs found" @page="f.page = $event" @retry="reload"
    @row-click="(r) => router.push(`${base}/jobs/${r.job.id}`)">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <SearchInput v-model="f.q" placeholder="Search title, company or skill" />
        <SelectFilter v-model="f.companyId" label="Company" :options="reference?.companies || []" />
        <SelectFilter v-model="f.archived" label="Archived" all-label="Hide archived" :options="[{ value: 'include', label: 'Include archived' }, { value: 'only', label: 'Only archived' }]" />
        <RouterLink v-if="embedded && auth.can('jobs.create')" :to="`${base}/jobs/new`" class="btn btn-primary ml-auto"><Plus class="size-4" /> New job</RouterLink>
      </div>
    </template>
    <template #cell-job="{ row }">
      <span class="flex items-center gap-3">
        <CompanyLogo :company="row.company" size="sm" />
        <span class="min-w-0"><span class="block font-medium">{{ row.job.title }}</span><span class="block text-xs text-muted">{{ row.company.name }} · {{ row.job.location }}</span></span>
      </span>
    </template>
    <template #cell-status="{ row }">
      <span class="flex flex-wrap gap-1"><StatusChip kind="job" :value="row.job.status" /><StatusChip v-if="row.job.archivedAt" tone="neutral" label="Archived" /></span>
    </template>
    <template #cell-applicants="{ row }">{{ row.applicantCount }}</template>
    <template #cell-deadline="{ row }">
      {{ formatDate(row.job.deadline) }}
      <span v-if="row.job.status === 'published'" class="block text-xs" :class="daysUntil(row.job.deadline) <= 3 ? 'text-red-700' : 'text-muted'">
        {{ daysUntil(row.job.deadline) > 0 ? `${daysUntil(row.job.deadline)} days left` : 'deadline passed' }}</span>
    </template>
    <template #cell-drive="{ row }">{{ formatDateTime(row.job.driveDate) }}</template>
    <template #cell-cgpa="{ row }">{{ row.job.eligibility.minCgpa }}</template>
    <template #cell-menu="{ row }">
      <RowMenu label="Job actions">
        <RouterLink :to="`${base}/jobs/${row.job.id}`" class="block rounded px-3 py-1.5 hover:bg-slate-50">View drive details</RouterLink>
        <RouterLink v-if="canEditJob(auth, row.job)" :to="`${base}/jobs/${row.job.id}/edit`" class="block rounded px-3 py-1.5 hover:bg-slate-50">Edit job</RouterLink>
        <template v-if="auth.can('drives.publish')">
          <button v-for="a in jobActions(row.job)" :key="a" class="block w-full rounded px-3 py-1.5 text-left hover:bg-slate-50"
            :class="a === 'cancel' && 'text-red-700'" @click="runAction(row.job, a)">{{ ACTION_INFO[a].label }}</button>
        </template>
      </RowMenu>
    </template>
  </DataTable>
  <JobActionDialog v-model:open="actionOpen" :job="action.job" :action="action.name" @done="reload" />
</template>
