<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, ArrowUp, Plus, Trash2 } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import FormField from '@/components/ui/FormField.vue'
import TagInput from '@/components/ui/TagInput.vue'
import Spinner from '@/components/ui/Spinner.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import LoadingBlock from '@/components/ui/LoadingBlock.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { jobsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { fromLocalInput, toLocalDateInput, toLocalInput } from '@/utils/format'
import { applyServerErrors } from '@/utils/validation'
import { SKILL_SUGGESTIONS } from '@/utils/suggestions'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const base = useBase()
const toast = useToast()
const reference = useReference().ref
const jobId = route.params.jobId
const editing = Boolean(jobId)
const YEARS = [2026, 2027, 2028, 2029]

const form = reactive({
  companyId: route.query.companyId || '', title: '', domain: 'Software', location: '', type: 'Full-time', description: '',
  responsibilities: '', skills: [], minCgpa: 6, maxActiveArrears: 0, maxArrearHistory: '', departmentIds: [], graduationYears: [2027],
  openDate: toLocalDateInput(new Date()), deadline: '', driveDate: '', ctcLpa: '', stipendPerMonth: '', rounds: [],
})
const errors = reactive({})
const original = ref(null)
const loading = ref(editing)
const loadError = ref(null)
const busy = ref(false)
const failure = ref('')
const publishOpen = ref(false)
const locked = computed(() => original.value && ['closed', 'cancelled'].includes(original.value.status))
const isPublished = computed(() => original.value?.status === 'published')

onMounted(async () => {
  if (!editing) { addRound('Online Assessment', 'Online'); addRound('Technical Interview', 'On-campus'); addRound('HR Interview', 'On-campus'); return }
  try {
    const { job } = await jobsApi.get(jobId)
    original.value = job
    Object.assign(form, {
      companyId: job.companyId, title: job.title, domain: job.domain, location: job.location, type: job.type, description: job.description,
      responsibilities: job.responsibilities.join('\n'), skills: [...job.skills], minCgpa: job.eligibility.minCgpa,
      maxActiveArrears: job.eligibility.maxActiveArrears, maxArrearHistory: job.eligibility.maxArrearHistory ?? '',
      departmentIds: [...job.eligibility.departmentIds], graduationYears: [...job.eligibility.graduationYears],
      openDate: toLocalDateInput(job.openDate), deadline: toLocalInput(job.deadline), driveDate: toLocalInput(job.driveDate),
      ctcLpa: job.ctcLpa ?? '', stipendPerMonth: job.stipendPerMonth ?? '',
      rounds: job.rounds.map((r) => ({ name: r.name, mode: r.mode, date: toLocalInput(r.date), location: r.location || '' })),
    })
  } catch (e) { loadError.value = e } finally { loading.value = false }
})

function addRound(name = '', mode = 'Online') { form.rounds.push({ name, mode, date: '', location: '' }) }
function moveRound(i, d) { const r = form.rounds.splice(i, 1)[0]; form.rounds.splice(i + d, 0, r) }
function toggleIn(list, v) { const i = list.indexOf(v); i < 0 ? list.push(v) : list.splice(i, 1) }

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.companyId) errors.companyId = 'Choose a company'
  if (!form.title.trim()) errors.title = 'Enter the job title'
  if (!form.location.trim()) errors.location = 'Enter the location'
  if (!form.description.trim()) errors.description = 'Describe the role'
  if (form.minCgpa === '' || form.minCgpa < 0 || form.minCgpa > 10) errors.minCgpa = 'Between 0 and 10'
  if (form.maxActiveArrears === '' || form.maxActiveArrears < 0) errors.maxActiveArrears = '0 or more'
  if (form.maxArrearHistory !== '' && form.maxArrearHistory < 0) errors.maxArrearHistory = '0 or more'
  if (!form.departmentIds.length) errors.departmentIds = 'Choose at least one department'
  if (!form.graduationYears.length) errors.graduationYears = 'Choose at least one batch'
  if (!form.openDate) errors.openDate = 'Choose the opening date'
  if (!form.deadline) errors.deadline = 'Choose the deadline'
  else if (new Date(form.deadline) <= new Date(form.openDate)) errors.deadline = 'Must be after the opening date'
  if (form.ctcLpa !== '' && form.ctcLpa < 0.1) errors.ctcLpa = 'At least 0.1'
  if (form.stipendPerMonth !== '' && form.stipendPerMonth < 0) errors.stipendPerMonth = '0 or more'
  form.rounds.forEach((r, i) => { if (!r.name.trim()) errors[`round${i}`] = 'Name this round' })
  return !Object.keys(errors).length
}

function body(status) {
  const num = (v) => (v === '' || v === null ? null : Number(v))
  return {
    companyId: Number(form.companyId), title: form.title.trim(), domain: form.domain.trim() || 'General', location: form.location.trim(),
    type: form.type, description: form.description.trim(),
    responsibilities: form.responsibilities.split('\n').map((s) => s.trim()).filter(Boolean), skills: form.skills,
    eligibility: {
      minCgpa: Number(form.minCgpa), maxActiveArrears: Number(form.maxActiveArrears), maxArrearHistory: num(form.maxArrearHistory),
      departmentIds: form.departmentIds.map(Number), graduationYears: form.graduationYears,
    },
    rounds: form.rounds.map((r) => ({ name: r.name.trim(), mode: r.mode, date: fromLocalInput(r.date), location: r.location || null })),
    ctcLpa: num(form.ctcLpa), stipendPerMonth: num(form.stipendPerMonth),
    openDate: fromLocalInput(form.openDate + 'T00:00'), deadline: fromLocalInput(form.deadline), driveDate: fromLocalInput(form.driveDate),
    status,
  }
}

async function save(status) {
  if (!validate()) { toast.error('Please fix the highlighted fields'); throw new Error('Please fix the highlighted fields.') }
  busy.value = true
  failure.value = ''
  try {
    const job = editing ? await jobsApi.update(jobId, body(status)) : await jobsApi.create(body(status))
    toast.success(status === 'published' && !isPublished.value ? 'Job published' : 'Job saved')
    router.push(`${base.value}/jobs/${job.id}`)
  } catch (e) {
    applyServerErrors(errors, e)
    failure.value = e.message
    throw e
  } finally { busy.value = false }
}
const saveDraft = () => save(isPublished.value ? 'published' : 'draft').catch(() => {})
</script>

<template>
  <PageHeader :title="editing ? 'Edit job' : 'New job'"
    :crumbs="[{ label: 'Jobs', to: `${base}/jobs` }, { label: editing ? original?.title || 'Edit' : 'New job' }]" />
  <LoadingBlock v-if="loading" :rows="10" />
  <ErrorState v-else-if="loadError" :error="loadError" />
  <form v-else class="space-y-6" novalidate @submit.prevent="saveDraft">
    <p v-if="locked" class="alert alert-warning">This job is {{ original.status }} and can no longer be edited.</p>
    <p v-if="failure" class="alert alert-error">{{ failure }}</p>
    <fieldset :disabled="locked" class="space-y-6">
      <SectionCard title="Role details">
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField label="Company" :error="errors.companyId" for="j-co" required>
            <select id="j-co" v-model="form.companyId" class="input" :disabled="editing && original?.status !== 'draft'">
              <option value="">Choose…</option>
              <option v-for="c in reference?.companies || []" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </FormField>
          <FormField label="Job title" :error="errors.title" for="j-title" required><input id="j-title" v-model="form.title" class="input" maxlength="160" /></FormField>
          <FormField label="Domain" for="j-domain"><input id="j-domain" v-model="form.domain" class="input" maxlength="80" /></FormField>
          <FormField label="Location" :error="errors.location" for="j-loc" required><input id="j-loc" v-model="form.location" class="input" /></FormField>
          <FormField label="Employment type" for="j-type">
            <select id="j-type" v-model="form.type" class="input"><option>Full-time</option><option>Internship</option><option>Internship + PPO</option></select>
          </FormField>
          <FormField label="Skills">
            <TagInput v-model="form.skills" :suggestions="SKILL_SUGGESTIONS" placeholder="e.g. Java" :disabled="locked" />
          </FormField>
          <FormField class="sm:col-span-2" label="Description" :error="errors.description" for="j-desc" required>
            <textarea id="j-desc" v-model="form.description" rows="4" class="input" maxlength="8000" />
          </FormField>
          <FormField class="sm:col-span-2" label="Responsibilities" hint="One per line" for="j-resp">
            <textarea id="j-resp" v-model="form.responsibilities" rows="3" class="input" />
          </FormField>
        </div>
      </SectionCard>

      <SectionCard title="Eligibility" subtitle="Checked automatically for every student; the AI assistant uses the same rules.">
        <div class="grid gap-4 sm:grid-cols-3">
          <FormField label="Minimum CGPA" :error="errors.minCgpa" for="j-cgpa" required><input id="j-cgpa" v-model.number="form.minCgpa" type="number" step="0.1" min="0" max="10" class="input" /></FormField>
          <FormField label="Max active arrears" :error="errors.maxActiveArrears" for="j-aa" required><input id="j-aa" v-model.number="form.maxActiveArrears" type="number" min="0" class="input" /></FormField>
          <FormField label="Max arrear history" :error="errors.maxArrearHistory" hint="Leave empty for no limit" for="j-ah"><input id="j-ah" v-model="form.maxArrearHistory" type="number" min="0" class="input" /></FormField>
        </div>
        <FormField class="mt-4" label="Departments" :error="errors.departmentIds" required>
          <div class="flex flex-wrap gap-2">
            <button v-for="d in reference?.departments || []" :key="d.value" type="button" class="rounded-full border px-3 py-1 text-sm"
              :class="form.departmentIds.includes(d.value) ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-line'" :title="d.name"
              @click="toggleIn(form.departmentIds, d.value)">{{ d.label }}</button>
            <button type="button" class="link text-xs" @click="form.departmentIds = (reference?.departments || []).map((d) => d.value)">Select all</button>
          </div>
        </FormField>
        <FormField class="mt-4" label="Graduation batches" :error="errors.graduationYears" required>
          <div class="flex flex-wrap gap-4">
            <label v-for="y in YEARS" :key="y" class="flex items-center gap-2 text-sm">
              <input type="checkbox" class="checkbox" :checked="form.graduationYears.includes(y)" @change="toggleIn(form.graduationYears, y)" /> {{ y }}
            </label>
          </div>
        </FormField>
      </SectionCard>

      <SectionCard title="Schedule & compensation">
        <div class="grid gap-4 sm:grid-cols-3">
          <FormField label="Applications open" :error="errors.openDate" for="j-open" required><input id="j-open" v-model="form.openDate" type="date" class="input" /></FormField>
          <FormField label="Deadline" :error="errors.deadline" for="j-dl" required><input id="j-dl" v-model="form.deadline" type="datetime-local" class="input" /></FormField>
          <FormField label="Drive date" for="j-drive"><input id="j-drive" v-model="form.driveDate" type="datetime-local" class="input" /></FormField>
          <FormField label="CTC (LPA)" :error="errors.ctcLpa" for="j-ctc"><input id="j-ctc" v-model="form.ctcLpa" type="number" step="0.1" min="0" class="input" /></FormField>
          <FormField label="Stipend (₹/month)" :error="errors.stipendPerMonth" for="j-st"><input id="j-st" v-model="form.stipendPerMonth" type="number" min="0" class="input" /></FormField>
        </div>
      </SectionCard>

      <SectionCard title="Hiring rounds">
        <template #actions><button type="button" class="btn btn-secondary btn-sm" @click="addRound()"><Plus class="size-4" /> Add round</button></template>
        <p v-if="!form.rounds.length" class="text-sm text-muted">No rounds yet.</p>
        <ol class="space-y-3">
          <li v-for="(r, i) in form.rounds" :key="i" class="grid gap-3 rounded-xl border border-line p-3 sm:grid-cols-[auto_1fr_10rem_13rem_1fr_auto] sm:items-start">
            <span class="flex size-7 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700">{{ i + 1 }}</span>
            <FormField :error="errors[`round${i}`]"><input v-model="r.name" class="input" placeholder="Round name" :aria-label="`Round ${i + 1} name`" /></FormField>
            <select v-model="r.mode" class="input" aria-label="Mode"><option>Online</option><option>On-campus</option><option>Virtual</option></select>
            <input v-model="r.date" type="datetime-local" class="input" aria-label="Date and time" />
            <input v-model="r.location" class="input" placeholder="Location or link" aria-label="Location" />
            <div class="flex">
              <button type="button" class="btn-icon" :disabled="i === 0" aria-label="Move up" @click="moveRound(i, -1)"><ArrowUp class="size-4" /></button>
              <button type="button" class="btn-icon" :disabled="i === form.rounds.length - 1" aria-label="Move down" @click="moveRound(i, 1)"><ArrowDown class="size-4" /></button>
              <button type="button" class="btn-icon hover:text-red-700" aria-label="Remove round" @click="form.rounds.splice(i, 1)"><Trash2 class="size-4" /></button>
            </div>
          </li>
        </ol>
      </SectionCard>
    </fieldset>

    <div class="flex flex-wrap justify-end gap-2">
      <RouterLink :to="editing ? `${base}/jobs/${jobId}` : `${base}/jobs`" class="btn btn-secondary">Cancel</RouterLink>
      <template v-if="!locked">
        <button v-if="isPublished" type="submit" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Save changes</button>
        <template v-else>
          <button type="submit" class="btn btn-secondary" :disabled="busy"><Spinner v-if="busy" /> Save draft</button>
          <button v-if="auth.can('drives.publish')" type="button" class="btn btn-primary" :disabled="busy" @click="validate() ? (publishOpen = true) : toast.error('Please fix the highlighted fields')">Publish…</button>
        </template>
      </template>
    </div>
    <ConfirmDialog v-model:open="publishOpen" title="Publish this job?" confirm-label="Publish" :action="() => save('published')">
      Eligible students will see <b>{{ form.title }}</b> and can apply straight away.
    </ConfirmDialog>
  </form>
</template>
