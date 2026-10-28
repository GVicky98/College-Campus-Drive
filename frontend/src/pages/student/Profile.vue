<script setup>
import { computed, reactive, ref } from 'vue'
import { BadgeCheck, Lock, Upload } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import Tabs from '@/components/ui/Tabs.vue'
import FormField from '@/components/ui/FormField.vue'
import TagInput from '@/components/ui/TagInput.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import Spinner from '@/components/ui/Spinner.vue'
import UploadDialog from '@/components/UploadDialog.vue'
import DocumentPreviewDialog from '@/components/DocumentPreviewDialog.vue'
import { documentsApi, studentApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useToast } from '@/composables/toast'
import { formatDate } from '@/utils/format'
import { applyServerErrors, isUrl } from '@/utils/validation'
import { SKILL_SUGGESTIONS, INTEREST_SUGGESTIONS, ROLE_SUGGESTIONS } from '@/utils/suggestions'

const toast = useToast()
const { data: p, loading, error, reload } = useAsync(() => studentApi.profile())
const docs = useAsync(() => documentsApi.list({ mine: 'true', pageSize: 50 }))
const tab = ref('personal')
const tabs = [
  { value: 'personal', label: 'Personal' }, { value: 'academic', label: 'Academic' }, { value: 'skills', label: 'Skills & interests' },
  { value: 'resume', label: 'Resume & documents' }, { value: 'prefs', label: 'Placement preferences' },
]

const editing = ref(false)
const saving = ref(false)
const failure = ref('')
const form = reactive({})
const errors = reactive({})

function startEdit() {
  const s = p.value
  Object.assign(form, {
    phone: s.phone || '', portfolioUrl: s.portfolioUrl || '', degree: s.degree || 'B.E.', currentYear: s.currentYear,
    cgpa: s.academic.cgpa ?? '', activeArrears: s.academic.activeArrears, arrearHistory: s.academic.arrearHistory,
    skills: [...s.skills], interests: [...s.interests], preferredRoles: [...s.preferredRoles],
  })
  Object.keys(errors).forEach((k) => delete errors[k])
  failure.value = ''
  editing.value = true
}

const patch = computed(() => {
  if (!editing.value || !p.value) return {}
  const s = p.value
  const out = {}
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)
  if (form.phone !== (s.phone || '')) out.phone = form.phone
  if (form.portfolioUrl !== (s.portfolioUrl || '')) out.portfolioUrl = form.portfolioUrl
  if (form.degree !== s.degree) out.degree = form.degree
  if (Number(form.currentYear) !== s.currentYear) out.currentYear = Number(form.currentYear)
  if (form.cgpa !== '' && Number(form.cgpa) !== s.academic.cgpa) out.cgpa = Number(form.cgpa)
  if (Number(form.activeArrears) !== s.academic.activeArrears) out.activeArrears = Number(form.activeArrears)
  if (Number(form.arrearHistory) !== s.academic.arrearHistory) out.arrearHistory = Number(form.arrearHistory)
  for (const k of ['skills', 'interests', 'preferredRoles']) if (!same(form[k], s[k])) out[k] = form[k]
  return out
})
const dirty = computed(() => Object.keys(patch.value).length > 0)

function validate() {
  errors.phone = !form.phone || /^\+?[0-9 ]{10,15}$/.test(form.phone) ? '' : 'Use 10–15 digits, optionally starting with +'
  errors.portfolioUrl = !form.portfolioUrl || isUrl(form.portfolioUrl) ? '' : 'Use a full link starting with http:// or https://'
  errors.currentYear = form.currentYear >= 1 && form.currentYear <= 6 ? '' : 'Between 1 and 6'
  errors.cgpa = form.cgpa === '' || (form.cgpa >= 0 && form.cgpa <= 10) ? '' : 'Between 0 and 10'
  errors.activeArrears = Number.isInteger(Number(form.activeArrears)) && form.activeArrears >= 0 ? '' : 'A whole number, 0 or more'
  errors.arrearHistory = Number.isInteger(Number(form.arrearHistory)) && form.arrearHistory >= 0 ? '' : 'A whole number, 0 or more'
  return !Object.values(errors).some(Boolean)
}

async function save() {
  if (!validate()) { toast.error('Please fix the highlighted fields'); return }
  saving.value = true
  failure.value = ''
  try {
    p.value = await studentApi.updateProfile(patch.value)
    editing.value = false
    toast.success('Profile saved')
  } catch (e) {
    applyServerErrors(errors, e)
    failure.value = e.message
  } finally {
    saving.value = false
  }
}

const uploadOpen = ref(false)
const previewId = ref(null)
const previewOpen = ref(false)
async function onUploaded() { toast.success('Document uploaded'); await reload(); docs.reload() }
const DEGREES = ['B.E.', 'B.Tech', 'M.E.', 'M.Tech', 'MBA', 'MCA']
</script>

<template>
  <PageHeader title="My Profile" subtitle="Keep this up to date: eligibility is checked against it.">
    <template #actions>
      <template v-if="editing">
        <button class="btn btn-secondary" :disabled="saving" @click="editing = false">Cancel</button>
        <button class="btn btn-primary" :disabled="!dirty || saving" @click="save"><Spinner v-if="saving" /> Save changes</button>
      </template>
      <button v-else-if="p" class="btn btn-primary" @click="startEdit">Edit profile</button>
    </template>
  </PageHeader>

  <AsyncBlock :loading="loading" :error="error" :has-data="!!p" :rows="8" @retry="reload">
    <div v-if="p" class="grid gap-6 lg:grid-cols-3">
      <div class="space-y-4 lg:order-2">
        <div class="card p-5">
          <div class="flex items-center justify-between"><p class="text-sm font-medium">Profile completion</p><StatusChip kind="placement" :value="p.placementStatus" /></div>
          <p class="mt-1 text-3xl font-semibold">{{ p.profileCompletion }}%</p>
          <div class="mt-3 h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full bg-brand-600" :style="{ width: p.profileCompletion + '%' }" /></div>
          <p v-if="p.missing.length" class="mt-3 text-xs text-muted">Still missing: {{ p.missing.join(', ') }}</p>
        </div>
      </div>

      <div class="lg:col-span-2">
        <p v-if="failure" class="alert alert-error mb-4">{{ failure }}</p>
        <Tabs v-model="tab" :tabs="tabs" />

        <SectionCard v-if="tab === 'personal'">
          <div class="grid gap-4 sm:grid-cols-2">
            <FormField label="Full name"><p class="input flex items-center gap-2 bg-slate-50"><Lock class="size-3.5 text-slate-400" />{{ p.name }}</p></FormField>
            <FormField label="College e-mail"><p class="input flex items-center gap-2 bg-slate-50"><Lock class="size-3.5 text-slate-400" />{{ p.email }}</p></FormField>
            <FormField label="Student ID" hint="Managed by the placement cell"><p class="input flex items-center gap-2 bg-slate-50"><Lock class="size-3.5 text-slate-400" />{{ p.studentCode }}</p></FormField>
            <FormField label="Phone" :error="errors.phone" for="phone">
              <input v-if="editing" id="phone" v-model="form.phone" class="input" placeholder="+91 98765 43210" />
              <p v-else class="input bg-slate-50">{{ p.phone || '—' }}</p>
            </FormField>
          </div>
        </SectionCard>

        <SectionCard v-if="tab === 'academic'">
          <p v-if="editing" class="alert alert-warning mb-4">Changing your CGPA or active arrears marks your record as unverified until the placement cell checks it again.</p>
          <div class="grid gap-4 sm:grid-cols-2">
            <FormField label="Department" hint="Managed by the placement cell"><p class="input flex items-center gap-2 bg-slate-50"><Lock class="size-3.5 text-slate-400" />{{ p.departmentName }}</p></FormField>
            <FormField label="Graduation year" hint="Managed by the placement cell"><p class="input flex items-center gap-2 bg-slate-50"><Lock class="size-3.5 text-slate-400" />{{ p.graduationYear }}</p></FormField>
            <FormField label="Degree" for="degree">
              <select v-if="editing" id="degree" v-model="form.degree" class="input"><option v-for="d in DEGREES" :key="d">{{ d }}</option></select>
              <p v-else class="input bg-slate-50">{{ p.degree || '—' }}</p>
            </FormField>
            <FormField label="Current year" :error="errors.currentYear" for="cy">
              <input v-if="editing" id="cy" v-model.number="form.currentYear" type="number" min="1" max="6" class="input" />
              <p v-else class="input bg-slate-50">{{ p.currentYear }}</p>
            </FormField>
            <FormField label="CGPA" :error="errors.cgpa" for="cgpa">
              <input v-if="editing" id="cgpa" v-model.number="form.cgpa" type="number" min="0" max="10" step="0.01" class="input" />
              <p v-else class="input flex items-center gap-2 bg-slate-50">
                {{ p.academic.cgpa ?? 'Missing' }}
                <StatusChip v-if="p.academic.cgpa !== undefined" :tone="p.academic.cgpaVerified ? 'success' : 'warning'" :label="p.academic.cgpaVerified ? 'Verified' : 'Unverified'" />
                <BadgeCheck v-if="p.academic.cgpaVerified" class="size-4 text-green-600" />
              </p>
            </FormField>
            <FormField label="Active arrears" :error="errors.activeArrears" for="aa">
              <input v-if="editing" id="aa" v-model.number="form.activeArrears" type="number" min="0" class="input" />
              <p v-else class="input bg-slate-50">{{ p.academic.activeArrears }}</p>
            </FormField>
            <FormField label="Arrear history" :error="errors.arrearHistory" for="ah">
              <input v-if="editing" id="ah" v-model.number="form.arrearHistory" type="number" min="0" class="input" />
              <p v-else class="input bg-slate-50">{{ p.academic.arrearHistory }}</p>
            </FormField>
          </div>
        </SectionCard>

        <SectionCard v-if="tab === 'skills'">
          <div class="space-y-4">
            <FormField label="Skills" hint="Add at least 3. Press Enter after each.">
              <TagInput v-if="editing" v-model="form.skills" :suggestions="SKILL_SUGGESTIONS" placeholder="e.g. Python" />
              <TagInput v-else :model-value="p.skills" disabled />
            </FormField>
            <FormField label="Interests">
              <TagInput v-if="editing" v-model="form.interests" :suggestions="INTEREST_SUGGESTIONS" placeholder="e.g. Cloud" />
              <TagInput v-else :model-value="p.interests" disabled />
            </FormField>
          </div>
        </SectionCard>

        <SectionCard v-if="tab === 'resume'">
          <div class="space-y-5">
            <div class="flex flex-wrap items-center gap-3 rounded-xl border border-line p-4">
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium">Resume</p>
                <p class="text-xs text-muted">{{ p.resumeFile || 'No resume uploaded yet' }}</p>
              </div>
              <button class="btn btn-secondary btn-sm" @click="uploadOpen = true"><Upload class="size-4" /> Upload</button>
            </div>
            <FormField label="Portfolio / GitHub link" :error="errors.portfolioUrl" for="pf">
              <input v-if="editing" id="pf" v-model="form.portfolioUrl" class="input" placeholder="https://github.com/you" />
              <p v-else class="input bg-slate-50"><a v-if="p.portfolioUrl" :href="p.portfolioUrl" target="_blank" rel="noopener" class="link">{{ p.portfolioUrl }}</a><span v-else>—</span></p>
            </FormField>
            <div>
              <div class="mb-2 flex items-center justify-between"><p class="text-sm font-medium">My documents</p><RouterLink to="/student/documents" class="link text-xs">Document library</RouterLink></div>
              <p v-if="!docs.data.value?.items.length" class="text-sm text-muted">No documents yet.</p>
              <ul v-else class="divide-y divide-line rounded-xl border border-line">
                <li v-for="d in docs.data.value.items" :key="d.id" class="flex items-center gap-3 px-3 py-2 text-sm">
                  <button class="link min-w-0 flex-1 truncate text-left" @click="previewId = d.id; previewOpen = true">{{ d.title }}</button>
                  <StatusChip :label="d.type" tone="neutral" /><span class="text-xs text-muted">{{ formatDate(d.uploadedAt) }}</span>
                </li>
              </ul>
            </div>
          </div>
        </SectionCard>

        <SectionCard v-if="tab === 'prefs'">
          <div class="space-y-4">
            <FormField label="Preferred roles">
              <TagInput v-if="editing" v-model="form.preferredRoles" :suggestions="ROLE_SUGGESTIONS" placeholder="e.g. Software Engineer" />
              <TagInput v-else :model-value="p.preferredRoles" disabled />
            </FormField>
            <FormField label="Placement status" hint="Updated automatically from your applications and offers">
              <p class="input flex items-center gap-2 bg-slate-50"><Lock class="size-3.5 text-slate-400" /><StatusChip kind="placement" :value="p.placementStatus" /></p>
            </FormField>
          </div>
        </SectionCard>
      </div>
    </div>
  </AsyncBlock>

  <UploadDialog v-model:open="uploadOpen" default-type="resume" @uploaded="onUploaded" />
  <DocumentPreviewDialog v-model:open="previewOpen" :doc-id="previewId" />
</template>
