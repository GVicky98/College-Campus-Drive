<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Download } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EligibilityReasons from '@/components/EligibilityReasons.vue'
import { applicationsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { downloadText, formatCgpa, formatDate } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const toast = useToast()
const reference = useReference().ref
const canReview = auth.can('applications.review')
const f = reactive({ q: '', companyId: '', jobId: route.query.jobId || '', dept: '', status: '', eligibility: '', sort: 'recent', page: 1 })
watch(() => f.companyId, () => { if (f.jobId && !jobs.value.some((j) => j.value === f.jobId)) f.jobId = '' })
watch(() => [f.q, f.companyId, f.jobId, f.dept, f.status, f.eligibility, f.sort], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => applicationsApi.list({ ...f, pageSize: 10 }), { watch: f })
const jobs = computed(() => (reference.value?.jobs || []).filter((j) => !f.companyId || j.companyId === f.companyId))
const selected = ref([])

const columns = [
  { key: 'student', label: 'Student' }, { key: 'job', label: 'Company & job' }, { key: 'dept', label: 'Dept', hide: 'md' },
  { key: 'cgpa', label: 'CGPA', hide: 'sm' }, { key: 'elig', label: 'Eligibility' }, { key: 'applied', label: 'Applied', hide: 'lg' },
  { key: 'stage', label: 'Stage' },
]
const STAGES = ['applied', 'shortlisted', 'interview', 'selected', 'offer_received', 'rejected', 'withdrawn']
  .map((s) => ({ value: s, label: s.replace('_', ' ').replace(/^\w/, (c) => c.toUpperCase()) }))
const ELIG = [{ value: 'eligible', label: 'Eligible' }, { value: 'not_eligible', label: 'Not eligible' }, { value: 'profile_incomplete', label: 'Profile incomplete' }, { value: 'needs_verification', label: 'Needs verification' }]
const ACTIONS = [
  { status: 'shortlisted', label: 'Shortlist', tone: 'primary' }, { status: 'interview', label: 'Move to interview', tone: 'primary' },
  { status: 'selected', label: 'Mark selected', tone: 'primary' }, { status: 'rejected', label: 'Reject', tone: 'danger' },
]

// ---- eligibility snapshot
const eligOpen = ref(false)
const eligRow = ref(null)

// ---- bulk stage change
const stageOpen = ref(false)
const stageAction = ref(null)
const note = ref('')
const outcome = ref(null)
const outcomeOpen = ref(false)
function askStage(a) { stageAction.value = a; note.value = ''; stageOpen.value = true }
async function applyStage() {
  const result = await applicationsApi.updateStage({ ids: selected.value.map(Number), status: stageAction.value.status, note: note.value || undefined })
  handleOutcome(result)
}
function handleOutcome(result) {
  if (result.updated.length) toast.success(`${result.updated.length} applicant(s) updated and notified`)
  selected.value = result.failed.map((x) => x.id)
  if (result.failed.length) { outcome.value = result; outcomeOpen.value = true }
  reload()
}
const needsException = computed(() => outcome.value?.failed.some((x) => /exception/i.test(x.reason)))

// ---- exception
const exOpen = ref(false)
const ex = reactive({ reason: '', approvedBy: '' })
const exErrors = reactive({})
const exBusy = ref(false)
const exFailure = ref('')
function openException() {
  outcomeOpen.value = false
  Object.assign(ex, { reason: '', approvedBy: '' })
  exFailure.value = ''
  exOpen.value = true
}
async function submitException() {
  exErrors.reason = ex.reason.trim().length >= 10 ? '' : 'Explain the exception (at least 10 characters)'
  exErrors.approvedBy = ex.approvedBy.trim().length >= 3 ? '' : 'Who approved it?'
  if (exErrors.reason || exErrors.approvedBy) return
  exBusy.value = true
  try {
    const ids = outcome.value.failed.filter((x) => /exception/i.test(x.reason)).map((x) => Number(x.id))
    const result = await applicationsApi.updateStage({ ids, status: stageAction.value.status, note: note.value || undefined,
      exception: { reason: ex.reason.trim(), approvedBy: ex.approvedBy.trim() } })
    exOpen.value = false
    handleOutcome(result)
  } catch (e) { exFailure.value = e.message } finally { exBusy.value = false }
}

async function exportCsv() {
  try {
    const csv = await applicationsApi.exportCsv({ status: f.status, companyId: f.companyId, jobId: f.jobId, dept: f.dept })
    downloadText('applications.csv', csv)
  } catch (e) { toast.error(e.message) }
}
const name = (id) => data.value?.items.find((r) => r.application.id === id)?.student?.name || `#${id}`
</script>

<template>
  <PageHeader title="Applications & applicants" subtitle="Screen applicants, move them through the stages and grant exceptions.">
    <template #actions>
      <button v-if="auth.can('reports.view')" class="btn btn-secondary" @click="exportCsv"><Download class="size-4" /> Export CSV</button>
    </template>
  </PageHeader>
  <DataTable v-model:selected="selected" :columns="columns" :rows="data?.items || []" :row-key="(r) => r.application.id" :loading="loading" :error="error"
    :total="data?.total" :page="f.page" :page-size="10" :selectable="canReview" empty-title="No applications match"
    @page="f.page = $event" @retry="reload">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <SearchInput v-model="f.q" placeholder="Student, ID, company or job" />
        <SelectFilter v-model="f.companyId" label="Company" :options="reference?.companies || []" />
        <SelectFilter v-model="f.jobId" label="Job" :options="jobs" />
        <SelectFilter v-model="f.dept" label="Dept" :options="reference?.departments || []" />
        <SelectFilter v-model="f.status" label="Stage" :options="STAGES" />
        <SelectFilter v-model="f.eligibility" label="Eligibility" :options="ELIG" />
        <SelectFilter v-model="f.sort" label="Sort" all-label="Most recent" :options="[{ value: 'cgpa', label: 'CGPA high–low' }, { value: 'name', label: 'Name A–Z' }]" />
      </div>
      <div v-if="selected.length" class="mt-3 flex flex-wrap items-center gap-2 rounded-xl bg-brand-50 px-3 py-2">
        <span class="text-sm font-medium text-brand-700">{{ selected.length }} selected</span>
        <button v-for="a in ACTIONS" :key="a.status" class="btn btn-sm" :class="a.tone === 'danger' ? 'btn-danger' : 'btn-primary'" @click="askStage(a)">{{ a.label }}</button>
        <button class="btn btn-ghost btn-sm ml-auto" @click="selected = []">Clear</button>
      </div>
    </template>
    <template #cell-student="{ row }"><span class="font-medium">{{ row.student.name }}</span><span class="block text-xs text-muted">{{ row.student.studentCode }}</span></template>
    <template #cell-job="{ row }"><span>{{ row.company.name }}</span><span class="block text-xs text-muted">{{ row.job.title }}</span></template>
    <template #cell-dept="{ row }">{{ row.student.departmentCode }}</template>
    <template #cell-cgpa="{ row }">{{ formatCgpa(row.student.academic.cgpa) }}</template>
    <template #cell-elig="{ row }">
      <button v-if="row.application.eligibilitySnapshot" class="flex flex-col items-start gap-0.5" @click="eligRow = row; eligOpen = true">
        <StatusChip kind="eligibility" :value="row.application.eligibilitySnapshot.state" />
        <span v-if="row.application.eligibilitySnapshot.exceptionGranted" class="text-[11px] text-amber-700">exception granted</span>
      </button>
    </template>
    <template #cell-applied="{ row }">{{ formatDate(row.application.appliedAt) }}</template>
    <template #cell-stage="{ row }"><StatusChip kind="application" :value="row.application.status" /></template>
  </DataTable>

  <BaseDialog v-model:open="eligOpen" :title="`Eligibility at application — ${eligRow?.student.name || ''}`">
    <EligibilityReasons v-if="eligRow" :result="eligRow.application.eligibilitySnapshot" show-time />
  </BaseDialog>

  <ConfirmDialog v-model:open="stageOpen" :title="`${stageAction?.label} ${selected.length} applicant(s)?`" :confirm-label="stageAction?.label"
    :tone="stageAction?.tone === 'danger' ? 'danger' : 'primary'" :action="applyStage">
    <p>Each student gets a notification and the change is recorded in their history.</p>
    <FormField label="Note (optional, shown in the history)" for="stage-note"><input id="stage-note" v-model="note" class="input" maxlength="250" /></FormField>
  </ConfirmDialog>

  <BaseDialog v-model:open="outcomeOpen" title="Some applicants were not moved">
    <ul class="space-y-2 text-sm">
      <li v-for="x in outcome?.failed || []" :key="x.id"><b>{{ name(x.id) }}</b> — {{ x.reason }}</li>
    </ul>
    <template #footer>
      <button class="btn btn-secondary" @click="outcomeOpen = false">Close</button>
      <button v-if="needsException" class="btn btn-warning" @click="openException">Request exception…</button>
    </template>
  </BaseDialog>

  <BaseDialog v-model:open="exOpen" title="Record an eligibility exception" :persistent="exBusy">
    <div class="space-y-4">
      <p class="alert alert-warning">These applicants did not meet the rules when they applied. The exception is stored on their record and in the audit log.</p>
      <p v-if="exFailure" class="alert alert-error">{{ exFailure }}</p>
      <FormField label="Reason" :error="exErrors.reason" for="ex-r" required><textarea id="ex-r" v-model="ex.reason" rows="3" class="input" maxlength="300" /></FormField>
      <FormField label="Approved by" :error="exErrors.approvedBy" hint="Name and role, e.g. Dr. Rao (HOD, CSE)" for="ex-a" required><input id="ex-a" v-model="ex.approvedBy" class="input" maxlength="120" /></FormField>
    </div>
    <template #footer>
      <button class="btn btn-secondary" :disabled="exBusy" @click="exOpen = false">Cancel</button>
      <button class="btn btn-warning" :disabled="exBusy" @click="submitException"><Spinner v-if="exBusy" /> Apply with exception</button>
    </template>
  </BaseDialog>
</template>
