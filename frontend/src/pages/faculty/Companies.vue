<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Archive, ArchiveRestore, Pencil, Plus } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import CompanyDialog from './parts/CompanyDialog.vue'
import { companiesApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { useToast } from '@/composables/toast'

defineProps({ embedded: Boolean })
const auth = useAuthStore()
const base = useBase()
const router = useRouter()
const toast = useToast()
const canManage = auth.can('companies.manage')
const f = reactive({ q: '', industry: '', tier: '', archived: '', page: 1 })
watch(() => [f.q, f.industry, f.tier, f.archived], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => companiesApi.list({ ...f, pageSize: 10 }), { watch: f })

const columns = [
  { key: 'company', label: 'Company' }, { key: 'industry', label: 'Industry', hide: 'md' }, { key: 'tier', label: 'Tier' },
  { key: 'jobs', label: 'Jobs', hide: 'sm' }, { key: 'offers', label: 'Offers', hide: 'sm' }, { key: 'contact', label: 'Contact', hide: 'lg' },
  ...(canManage ? [{ key: 'actions', label: '', align: 'right' }] : []),
]
const dialogOpen = ref(false)
const editing = ref(null)
const archiving = ref(null)
const archiveOpen = ref(false)
function edit(c) { editing.value = c; dialogOpen.value = true }
async function toggleArchive() {
  const c = archiving.value
  await companiesApi.archive(c.id, !c.archivedAt)
  toast.success(c.archivedAt ? `${c.name} restored` : `${c.name} archived`)
  reload()
}
</script>

<template>
  <PageHeader v-if="!embedded" title="Companies" subtitle="Recruiters, their contacts and hiring history.">
    <template #actions><button v-if="canManage" class="btn btn-primary" @click="edit(null)"><Plus class="size-4" /> Add company</button></template>
  </PageHeader>
  <DataTable :columns="columns" :rows="data?.items || []" :row-key="(r) => r.company.id" :loading="loading" :error="error"
    :total="data?.total" :page="f.page" :page-size="10" clickable empty-title="No companies found"
    @page="f.page = $event" @retry="reload" @row-click="(r) => router.push(`${base}/companies/${r.company.id}`)">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <SearchInput v-model="f.q" placeholder="Search name or industry" />
        <SelectFilter v-model="f.industry" label="Industry" :options="data?.meta.industries || []" />
        <SelectFilter v-model="f.tier" label="Tier" :options="[{ value: 'regular', label: 'Regular' }, { value: 'dream', label: 'Dream' }, { value: 'super_dream', label: 'Super Dream' }]" />
        <SelectFilter v-model="f.archived" label="Archived" all-label="Hide archived" :options="[{ value: 'include', label: 'Include archived' }, { value: 'only', label: 'Only archived' }]" />
        <button v-if="embedded && canManage" class="btn btn-primary ml-auto" @click="edit(null)"><Plus class="size-4" /> Add company</button>
      </div>
    </template>
    <template #cell-company="{ row }">
      <span class="flex items-center gap-3">
        <CompanyLogo :company="row.company" size="sm" />
        <span class="min-w-0">
          <span class="flex items-center gap-2 font-medium">{{ row.company.name }}<StatusChip v-if="row.company.archivedAt" tone="neutral" label="Archived" /></span>
          <a :href="row.company.website" target="_blank" rel="noopener" class="text-xs text-muted hover:underline" @click.stop>{{ row.company.website.replace(/^https?:\/\//, '') }}</a>
        </span>
      </span>
    </template>
    <template #cell-industry="{ row }">{{ row.company.industry }}</template>
    <template #cell-tier="{ row }"><StatusChip kind="tier" :value="row.company.tier" /></template>
    <template #cell-jobs="{ row }">{{ row.activeJobs }} active / {{ row.jobCount }}</template>
    <template #cell-offers="{ row }">{{ row.offers }}</template>
    <template #cell-contact="{ row }"><span class="text-sm">{{ row.company.contactName }}</span><span class="block text-xs text-muted">{{ row.company.contactEmail }}</span></template>
    <template #cell-actions="{ row }">
      <div class="flex justify-end" @click.stop>
        <button v-if="!row.company.archivedAt" class="btn-icon" aria-label="Edit company" @click="edit(row.company)"><Pencil class="size-4" /></button>
        <button class="btn-icon" :aria-label="row.company.archivedAt ? 'Restore company' : 'Archive company'" @click="archiving = row.company; archiveOpen = true">
          <component :is="row.company.archivedAt ? ArchiveRestore : Archive" class="size-4" />
        </button>
      </div>
    </template>
  </DataTable>
  <CompanyDialog v-model:open="dialogOpen" :company="editing" @saved="toast.success('Company saved'); reload()" />
  <ConfirmDialog v-model:open="archiveOpen" :title="archiving?.archivedAt ? 'Restore company?' : 'Archive company?'"
    :confirm-label="archiving?.archivedAt ? 'Restore' : 'Archive'" :tone="archiving?.archivedAt ? 'primary' : 'warning'" :action="toggleArchive">
    <p v-if="archiving?.archivedAt">{{ archiving?.name }} will appear in lists again and can be edited.</p>
    <p v-else>{{ archiving?.name }} will be hidden from lists and become read-only. Its history is kept. Companies with published jobs cannot be archived.</p>
  </ConfirmDialog>
</template>
