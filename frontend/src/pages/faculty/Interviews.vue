<script setup>
import { computed, ref } from 'vue'
import { Plus } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import InterviewCalendar from './parts/InterviewCalendar.vue'
import InterviewDialog from './parts/InterviewDialog.vue'
import { applicationsApi, interviewsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/toast'
import { formatDateTime, timeAgo } from '@/utils/format'

const auth = useAuthStore()
const toast = useToast()
const canEdit = auth.can('applications.review')
const tab = ref('calendar')

async function loadAll() { // walk every page so the calendar is complete
  const out = []
  for (let page = 1; page <= 20; page++) {
    const r = await interviewsApi.list({ page, pageSize: 100 })
    out.push(...r.items)
    if (out.length >= r.total) break
  }
  return out
}
const { data, loading, error, reload } = useAsync(loadAll)
const results = useAsync(async () => {
  const [a, b] = await Promise.all([applicationsApi.list({ status: 'selected', pageSize: 100 }), applicationsApi.list({ status: 'offer_received', pageSize: 100 })])
  return [...a.items, ...b.items].sort((x, y) => y.application.updatedAt.localeCompare(x.application.updatedAt))
})

const detail = ref(null)
const detailOpen = ref(false)
const dialogOpen = ref(false)
const editing = ref(null)
const confirm = ref({ open: false, title: '', label: '', tone: 'primary', run: null, text: '' })
const started = computed(() => detail.value && new Date(detail.value.interview.at) <= new Date())

function open(v) { detail.value = v; detailOpen.value = true }
function schedule(v = null) { editing.value = v; detailOpen.value = false; dialogOpen.value = true }
function ask(title, label, tone, text, run) { confirm.value = { open: true, title, label, tone, text, run } }
const setStatus = (status, label, tone, text) => ask(`${label}?`, label, tone, text, async () => {
  await interviewsApi.setStatus(detail.value.interview.id, status)
  toast.success(`Marked ${label.toLowerCase()}`)
  detailOpen.value = false
  reload()
})
const notify = () => ask(detail.value.interview.notified ? 'Notify students again?' : 'Notify students?', 'Send notification', 'primary',
  'Each candidate gets an in-app notification with the time and place.', async () => {
    const { notified } = await interviewsApi.notify(detail.value.interview.id)
    toast.success(`${notified} student(s) notified`)
    detailOpen.value = false
    reload()
  })
async function onSaved() { toast.success('Interview saved. Remember to notify the students.'); reload() }

const listCols = [
  { key: 'round', label: 'Round' }, { key: 'when', label: 'Date & time' }, { key: 'where', label: 'Location', hide: 'md' },
  { key: 'candidates', label: 'Candidates', align: 'right' }, { key: 'status', label: 'Status' }, { key: 'notified', label: 'Notified', hide: 'sm' },
]
const resultCols = [{ key: 'student', label: 'Student' }, { key: 'job', label: 'Company & job' }, { key: 'outcome', label: 'Outcome' }, { key: 'updated', label: 'Updated', hide: 'sm' }]
</script>

<template>
  <PageHeader title="Interviews & selection" subtitle="Schedule rounds, notify candidates and record outcomes.">
    <template #actions><button v-if="canEdit" class="btn btn-primary" @click="schedule()"><Plus class="size-4" /> Schedule interview</button></template>
  </PageHeader>
  <Tabs v-model="tab" :tabs="[{ value: 'calendar', label: 'Calendar' }, { value: 'list', label: 'Schedule list' }, { value: 'results', label: 'Selection results' }]" />

  <AsyncBlock v-if="tab !== 'results'" :loading="loading" :error="error" :has-data="!!data" @retry="reload">
    <InterviewCalendar v-if="tab === 'calendar'" :items="data" @open="open" />
    <DataTable v-else :columns="listCols" :rows="data" :row-key="(r) => r.interview.id" clickable empty-title="No interviews scheduled" @row-click="open">
      <template #cell-round="{ row }"><span class="font-medium">{{ row.interview.round }}</span><span class="block text-xs text-muted">{{ row.company.name }} — {{ row.job.title }}</span></template>
      <template #cell-when="{ row }">{{ formatDateTime(row.interview.at) }}<span class="block text-xs text-muted">{{ row.interview.durationMins }} min</span></template>
      <template #cell-where="{ row }">{{ /^https?:/.test(row.interview.location) ? 'Meeting link' : row.interview.location }}</template>
      <template #cell-candidates="{ row }">{{ row.candidates.length }}</template>
      <template #cell-status="{ row }"><StatusChip kind="interview" :value="row.interview.status" /></template>
      <template #cell-notified="{ row }"><StatusChip :tone="row.interview.notified ? 'success' : 'warning'" :label="row.interview.notified ? 'Notified' : 'Not yet'" /></template>
    </DataTable>
  </AsyncBlock>
  <DataTable v-else :columns="resultCols" :rows="results.data.value || []" :row-key="(r) => r.application.id" :loading="results.loading.value"
    :error="results.error.value" empty-title="No selections yet" @retry="results.reload">
    <template #cell-student="{ row }"><span class="font-medium">{{ row.student.name }}</span><span class="block text-xs text-muted">{{ row.student.studentCode }}</span></template>
    <template #cell-job="{ row }">{{ row.company.name }} — {{ row.job.title }}</template>
    <template #cell-outcome="{ row }"><StatusChip kind="application" :value="row.application.status" /></template>
    <template #cell-updated="{ row }">{{ timeAgo(row.application.updatedAt) }}</template>
  </DataTable>

  <BaseDialog v-model:open="detailOpen" :title="detail ? `${detail.interview.round} — ${detail.company.name}` : ''" size="lg">
    <div v-if="detail" class="space-y-4 text-sm">
      <dl class="grid gap-3 sm:grid-cols-2">
        <div><dt class="text-xs text-muted">Job</dt><dd>{{ detail.job.title }}</dd></div>
        <div><dt class="text-xs text-muted">When</dt><dd>{{ formatDateTime(detail.interview.at) }} · {{ detail.interview.durationMins }} min</dd></div>
        <div><dt class="text-xs text-muted">Where</dt><dd class="break-all">
          <a v-if="/^https?:/.test(detail.interview.location)" :href="detail.interview.location" target="_blank" rel="noopener" class="link">{{ detail.interview.location }}</a>
          <span v-else>{{ detail.interview.location }}</span></dd></div>
        <div><dt class="text-xs text-muted">Status</dt><dd class="flex gap-2"><StatusChip kind="interview" :value="detail.interview.status" />
          <StatusChip :tone="detail.interview.notified ? 'success' : 'warning'" :label="detail.interview.notified ? 'Students notified' : 'Not notified'" /></dd></div>
      </dl>
      <div>
        <p class="mb-2 font-medium">Candidates ({{ detail.candidates.length }})</p>
        <ul class="divide-y divide-line rounded-xl border border-line">
          <li v-for="c in detail.candidates" :key="c.applicationId" class="flex items-center justify-between px-3 py-2">
            <span>{{ c.name }} <span class="text-xs text-muted">{{ c.studentCode }}</span></span><StatusChip kind="application" :value="c.status" />
          </li>
        </ul>
        <p class="hint mt-2">Record each candidate's result on the Applications page (shortlist, select or reject).</p>
      </div>
    </div>
    <template v-if="detail && canEdit && detail.interview.status === 'scheduled'" #footer>
      <button class="btn btn-ghost text-red-700" @click="setStatus('cancelled', 'Cancel round', 'danger', 'Notified candidates are told it is cancelled.')">Cancel round</button>
      <button class="btn btn-secondary" :disabled="!started" @click="setStatus('no_show', 'No-show', 'warning', 'Record that this round did not take place with the candidates.')">No-show</button>
      <button class="btn btn-secondary" :disabled="!started" @click="setStatus('completed', 'Completed', 'primary', 'The round is marked as held.')">Mark completed</button>
      <button class="btn btn-secondary" @click="schedule(detail)">Edit</button>
      <button class="btn btn-primary" @click="notify">{{ detail.interview.notified ? 'Re-notify' : 'Notify students' }}</button>
    </template>
  </BaseDialog>

  <InterviewDialog v-model:open="dialogOpen" :interview="editing" @saved="onSaved" />
  <ConfirmDialog v-model:open="confirm.open" :title="confirm.title" :confirm-label="confirm.label" :tone="confirm.tone" :action="confirm.run">{{ confirm.text }}</ConfirmDialog>
</template>
