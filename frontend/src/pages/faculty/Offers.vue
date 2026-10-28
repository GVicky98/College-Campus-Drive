<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { CircleCheck, Gift, Handshake, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import RowMenu from '@/components/ui/RowMenu.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import ChartCard from '@/components/charts/ChartCard.vue'
import { offersApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { formatDate, formatPackage, toLocalDateInput } from '@/utils/format'

const auth = useAuthStore()
const toast = useToast()
const reference = useReference().ref
const canManage = auth.can('offers.manage')
const tab = ref('records')
const f = reactive({ q: '', status: '', dept: '', companyId: '', page: 1 })
watch(() => [f.q, f.status, f.dept, f.companyId], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => offersApi.list({ ...f, pageSize: 10 }), { watch: f })
const meta = computed(() => data.value?.meta)

const NEXT = { pending: ['received', 'withdrawn'], received: ['accepted', 'declined', 'withdrawn'], accepted: ['withdrawn'] }
const LABEL = { received: 'Mark received', accepted: 'Record acceptance', declined: 'Record decline', withdrawn: 'Withdraw offer' }
const columns = [
  { key: 'student', label: 'Student' }, { key: 'job', label: 'Company & job' }, { key: 'package', label: 'Package' },
  { key: 'date', label: 'Offer date', hide: 'lg' }, { key: 'by', label: 'Accept by', hide: 'md' }, { key: 'policy', label: 'Policy', hide: 'lg' },
  { key: 'status', label: 'Status' }, ...(canManage ? [{ key: 'menu', label: '', align: 'right' }] : []),
]
const waitingCols = [{ key: 'student', label: 'Student' }, { key: 'job', label: 'Company & job' }, { key: 'package', label: 'Advertised', hide: 'sm' },
  { key: 'since', label: 'Selected on', hide: 'md' }, { key: 'action', label: '', align: 'right' }]
const STATUSES = ['pending', 'received', 'accepted', 'declined', 'withdrawn'].map((s) => ({ value: s, label: s[0].toUpperCase() + s.slice(1) }))

// status change
const change = ref({ open: false, view: null, status: '' })
async function applyChange(reason) {
  await offersApi.setStatus(change.value.view.offer.id, change.value.status, reason || undefined)
  toast.success('Offer updated and the student notified')
  reload()
}

// create offer
const createOpen = ref(false)
const createFor = ref(null)
const form = reactive({ ctcLpa: '', acceptBy: '' })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const created = ref(null)
function openCreate(row) {
  createFor.value = row
  created.value = null
  failure.value = ''
  Object.assign(form, { ctcLpa: row.job.ctcLpa ?? '', acceptBy: toLocalDateInput(new Date(Date.now() + 14 * 86400000)) })
  createOpen.value = true
}
async function createOffer() {
  errors.ctcLpa = form.ctcLpa > 0 ? '' : 'Enter the package (more than 0)'
  errors.acceptBy = form.acceptBy && new Date(form.acceptBy + 'T23:59') > new Date() ? '' : 'Choose a future date'
  if (errors.ctcLpa || errors.acceptBy) return
  busy.value = true
  failure.value = ''
  try {
    created.value = await offersApi.create({ applicationId: Number(createFor.value.application.id), ctcLpa: Number(form.ctcLpa),
      acceptBy: new Date(form.acceptBy + 'T23:59').toISOString() })
    toast.success('Offer issued and the student notified')
    reload()
  } catch (e) { failure.value = e.message } finally { busy.value = false }
}
const deptRows = computed(() => meta.value?.byDept || [])
</script>

<template>
  <PageHeader title="Offers & placements" subtitle="Issue offers, record responses and see placement totals." />
  <Tabs v-model="tab" :tabs="[{ value: 'records', label: 'Offer records' }, { value: 'waiting', label: 'Selected, awaiting offer', count: meta?.selectedWithoutOffer.length }, { value: 'summary', label: 'Summaries' }]" />

  <DataTable v-if="tab === 'records'" :columns="columns" :rows="data?.items || []" :row-key="(r) => r.offer.id" :loading="loading" :error="error"
    :total="data?.total" :page="f.page" :page-size="10" empty-title="No offers yet" @page="f.page = $event" @retry="reload">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <SearchInput v-model="f.q" placeholder="Student, ID or company" />
        <SelectFilter v-model="f.status" label="Status" :options="STATUSES" />
        <SelectFilter v-model="f.dept" label="Dept" :options="reference?.departments || []" />
        <SelectFilter v-model="f.companyId" label="Company" :options="reference?.companies || []" />
      </div>
    </template>
    <template #cell-student="{ row }"><span class="font-medium">{{ row.student.name }}</span><span class="block text-xs text-muted">{{ row.student.studentCode }} · {{ row.student.departmentCode }}</span></template>
    <template #cell-job="{ row }">{{ row.company.name }}<span class="block text-xs text-muted">{{ row.job.title }}</span></template>
    <template #cell-package="{ row }">{{ formatPackage(row.offer.ctcLpa) }}</template>
    <template #cell-date="{ row }">{{ formatDate(row.offer.offeredAt) }}</template>
    <template #cell-by="{ row }">{{ formatDate(row.offer.acceptBy) }}</template>
    <template #cell-policy="{ row }">
      <span :title="row.offer.policyChecks.map((c) => `${c.passed ? '✓' : '✗'} ${c.label}: ${c.detail}`).join('\n') || 'No checks'" class="flex items-center gap-1 text-xs">
        <CircleCheck class="size-4 text-green-600" />{{ row.offer.policyChecks.filter((c) => c.passed).length }}/{{ row.offer.policyChecks.length }} passed</span>
    </template>
    <template #cell-status="{ row }"><StatusChip kind="offer" :value="row.offer.status" /></template>
    <template #cell-menu="{ row }">
      <RowMenu v-if="NEXT[row.offer.status]" label="Offer actions">
        <button v-for="s in NEXT[row.offer.status]" :key="s" class="block w-full rounded px-3 py-1.5 text-left hover:bg-slate-50" :class="s === 'withdrawn' && 'text-red-700'"
          @click="change = { open: true, view: row, status: s }">{{ LABEL[s] }}</button>
      </RowMenu>
    </template>
  </DataTable>

  <template v-else-if="tab === 'waiting'">
    <p class="alert alert-info mb-4">These applicants were marked selected but have no offer yet. Issuing an offer runs the placement-policy checks.</p>
    <DataTable :columns="waitingCols" :rows="meta?.selectedWithoutOffer || []" :row-key="(r) => r.application.id" :loading="loading" empty-title="Nobody is waiting">
      <template #cell-student="{ row }"><span class="font-medium">{{ row.student.name }}</span><span class="block text-xs text-muted">{{ row.student.studentCode }}</span></template>
      <template #cell-job="{ row }">{{ row.company.name }} — {{ row.job.title }}</template>
      <template #cell-package="{ row }">{{ formatPackage(row.job.ctcLpa, row.job.stipendPerMonth) }}</template>
      <template #cell-since="{ row }">{{ formatDate(row.application.updatedAt) }}</template>
      <template #cell-action="{ row }"><button v-if="canManage" class="btn btn-primary btn-sm" @click="openCreate(row)">Create offer</button></template>
    </DataTable>
  </template>

  <div v-else-if="meta" class="space-y-6">
    <div class="grid gap-4 sm:grid-cols-3">
      <MetricCard label="Unique students placed" :value="meta.totals.placed" :icon="Users" tone="green" />
      <MetricCard label="Total offers" :value="meta.totals.offers" :icon="Gift" />
      <MetricCard label="Accepted offers" :value="meta.totals.accepted" :icon="Handshake" tone="purple" />
    </div>
    <div class="grid gap-6 lg:grid-cols-2">
      <ChartCard title="Department-wise" type="bar" :labels="deptRows.map((d) => d.dept)"
        :series="[{ name: 'Offers', values: deptRows.map((d) => d.offers) }, { name: 'Students placed', values: deptRows.map((d) => d.placed) }]" />
      <ChartCard title="Company-wise" type="hbar" :labels="meta.byCompany.map((c) => c.company)"
        :series="[{ name: 'Offers', values: meta.byCompany.map((c) => c.offers) }, { name: 'Accepted', values: meta.byCompany.map((c) => c.accepted) }]" />
    </div>
    <SectionCard title="By department" :padded="false">
      <table class="table">
        <thead><tr><th>Department</th><th class="text-right">Students</th><th class="text-right">Offers</th><th class="text-right">Placed</th><th class="text-right">Placement %</th></tr></thead>
        <tbody><tr v-for="d in deptRows" :key="d.dept"><td>{{ d.dept }}</td><td class="text-right">{{ d.students }}</td><td class="text-right">{{ d.offers }}</td>
          <td class="text-right">{{ d.placed }}</td><td class="text-right">{{ d.students ? ((100 * d.placed) / d.students).toFixed(1) : '0.0' }}%</td></tr></tbody>
      </table>
    </SectionCard>
  </div>

  <ConfirmDialog v-model:open="change.open" :title="`${LABEL[change.status] || ''}?`" :confirm-label="LABEL[change.status] || 'Confirm'"
    :tone="change.status === 'withdrawn' ? 'danger' : 'primary'" :require-reason="change.status === 'withdrawn'" reason-label="Reason (sent to the student)" :action="applyChange">
    <p v-if="change.view"><b>{{ change.view.student.name }}</b> — {{ change.view.company.name }}, {{ formatPackage(change.view.offer.ctcLpa) }}</p>
    <p v-if="change.status === 'accepted'" class="text-muted">Use this to record an acceptance received offline. Policy limits are checked again.</p>
  </ConfirmDialog>

  <BaseDialog v-model:open="createOpen" :title="created ? 'Offer issued' : 'Create offer'" :persistent="busy">
    <div v-if="created" class="space-y-3 text-sm">
      <p class="alert alert-success">{{ created.student.name }} has been notified.</p>
      <p class="font-medium">Policy checks</p>
      <ul><li v-for="c in created.offer.policyChecks" :key="c.label">{{ c.passed ? '✓' : '✗' }} {{ c.label }} — {{ c.detail }}</li>
        <li v-if="!created.offer.policyChecks.length" class="text-muted">No offer policies apply.</li></ul>
    </div>
    <form v-else-if="createFor" id="offer-form" class="space-y-4" novalidate @submit.prevent="createOffer">
      <p class="text-sm"><b>{{ createFor.student.name }}</b> — {{ createFor.company.name }}, {{ createFor.job.title }}</p>
      <p v-if="failure" class="alert alert-error">{{ failure }}</p>
      <FormField label="Package (LPA)" :error="errors.ctcLpa" for="o-ctc" required><input id="o-ctc" v-model.number="form.ctcLpa" type="number" step="0.1" min="0" class="input" /></FormField>
      <FormField label="Acceptance deadline" :error="errors.acceptBy" hint="The student can respond until 23:59 on this day" for="o-by" required><input id="o-by" v-model="form.acceptBy" type="date" class="input" /></FormField>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="createOpen = false">{{ created ? 'Close' : 'Cancel' }}</button>
      <button v-if="!created" type="submit" form="offer-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Issue offer</button>
    </template>
  </BaseDialog>
</template>
