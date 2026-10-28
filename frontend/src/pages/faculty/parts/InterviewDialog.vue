<script setup>
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { applicationsApi, interviewsApi, jobsApi } from '@/api'
import { fromLocalInput, toLocalInput } from '@/utils/format'
import { applyServerErrors } from '@/utils/validation'

const props = defineProps({ open: Boolean, interview: Object }) // interview view when editing
const emit = defineEmits(['update:open', 'saved'])
const form = reactive({ jobId: '', round: '', at: '', durationMins: 45, location: '', applicationIds: [] })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const jobs = ref([])
const applicants = ref([])
const editing = computed(() => Boolean(props.interview))
const rounds = computed(() => jobs.value.find((v) => v.job.id === form.jobId)?.job.rounds.map((r) => r.name) || [])

watch(() => props.open, async (v) => {
  if (!v) return
  failure.value = ''
  Object.keys(errors).forEach((k) => delete errors[k])
  const i = props.interview?.interview
  Object.assign(form, i
    ? { jobId: i.jobId, round: i.round, at: toLocalInput(i.at), durationMins: i.durationMins, location: i.location, applicationIds: [...i.applicationIds] }
    : { jobId: '', round: '', at: '', durationMins: 45, location: '', applicationIds: [] })
  const [pub, closed] = await Promise.all([jobsApi.list({ status: 'published', pageSize: 100 }), jobsApi.list({ status: 'closed', pageSize: 100 })])
  jobs.value = [...pub.items, ...closed.items]
  if (form.jobId) loadApplicants()
})
watch(() => form.jobId, (now, before) => { if (before && now !== before) form.applicationIds = []; loadApplicants() })

async function loadApplicants() {
  if (!form.jobId) { applicants.value = []; return }
  const [a, b] = await Promise.all([
    applicationsApi.list({ jobId: form.jobId, status: 'shortlisted', pageSize: 100 }),
    applicationsApi.list({ jobId: form.jobId, status: 'interview', pageSize: 100 }),
  ])
  applicants.value = [...a.items, ...b.items]
}
function toggle(id) { const i = form.applicationIds.indexOf(id); i < 0 ? form.applicationIds.push(id) : form.applicationIds.splice(i, 1) }

async function save() {
  errors.jobId = form.jobId ? '' : 'Choose a job'
  errors.round = form.round.trim() ? '' : 'Name the round'
  errors.at = form.at ? '' : 'Pick the date and time'
  errors.durationMins = form.durationMins >= 5 ? '' : 'At least 5 minutes'
  errors.location = form.location.trim() ? '' : 'Enter a room or meeting link'
  errors.applicationIds = form.applicationIds.length ? '' : 'Choose at least one candidate'
  if (Object.values(errors).some(Boolean)) return
  busy.value = true
  failure.value = ''
  const body = { jobId: Number(form.jobId), round: form.round.trim(), at: fromLocalInput(form.at), durationMins: Number(form.durationMins),
    location: form.location.trim(), applicationIds: form.applicationIds.map(Number) }
  try {
    const saved = editing.value ? await interviewsApi.update(props.interview.interview.id, body) : await interviewsApi.create(body)
    emit('saved', saved)
    emit('update:open', false)
  } catch (e) { applyServerErrors(errors, e); failure.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <BaseDialog :open="open" :title="editing ? 'Edit interview' : 'Schedule interview'" size="lg" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="iv-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="save">
      <p v-if="failure" class="alert alert-error sm:col-span-2">{{ failure }}</p>
      <FormField class="sm:col-span-2" label="Job" :error="errors.jobId" for="iv-job" required>
        <select id="iv-job" v-model="form.jobId" class="input" :disabled="editing">
          <option value="">Choose a published or closed job…</option>
          <option v-for="v in jobs" :key="v.job.id" :value="v.job.id">{{ v.company.name }} — {{ v.job.title }}</option>
        </select>
      </FormField>
      <FormField label="Round" :error="errors.round" for="iv-round" required>
        <input id="iv-round" v-model="form.round" list="iv-rounds" class="input" placeholder="e.g. Technical Interview" />
        <datalist id="iv-rounds"><option v-for="r in rounds" :key="r" :value="r" /></datalist>
      </FormField>
      <FormField label="Date & time" :error="errors.at" for="iv-at" required><input id="iv-at" v-model="form.at" type="datetime-local" class="input" /></FormField>
      <FormField label="Duration (minutes)" :error="errors.durationMins" for="iv-dur"><input id="iv-dur" v-model.number="form.durationMins" type="number" min="5" step="5" class="input" /></FormField>
      <FormField label="Location or link" :error="errors.location" for="iv-loc" required><input id="iv-loc" v-model="form.location" class="input" /></FormField>
      <FormField class="sm:col-span-2" label="Candidates" :error="errors.applicationIds" hint="Shortlisted and interview-stage applicants of this job" required>
        <p v-if="!form.jobId" class="text-sm text-muted">Choose a job first.</p>
        <p v-else-if="!applicants.length" class="text-sm text-muted">No shortlisted applicants for this job yet.</p>
        <div v-else class="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-line p-2">
          <label v-for="a in applicants" :key="a.application.id" class="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50">
            <input type="checkbox" class="checkbox" :checked="form.applicationIds.includes(a.application.id)" @change="toggle(a.application.id)" />
            {{ a.student.name }} <span class="text-xs text-muted">{{ a.student.studentCode }} · {{ a.application.status }}</span>
          </label>
        </div>
      </FormField>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="iv-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> {{ editing ? 'Save changes' : 'Schedule' }}</button>
    </template>
  </BaseDialog>
</template>
