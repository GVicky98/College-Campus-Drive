<script setup>
// Three-step first-run setup for students: academics → skills → resume & links.
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { GraduationCap } from '@lucide/vue'
import FormField from '@/components/ui/FormField.vue'
import TagInput from '@/components/ui/TagInput.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { documentsApi, studentApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { applyServerErrors, isUrl } from '@/utils/validation'
import { INTEREST_SUGGESTIONS, ROLE_SUGGESTIONS, SKILL_SUGGESTIONS } from '@/utils/suggestions'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()
const reference = useReference().ref
const step = ref(0)
const steps = ['Academics', 'Skills & interests', 'Resume & links']
const busy = ref(false)
const failure = ref('')
const errors = reactive({})
const form = reactive({
  studentCode: '', departmentId: auth.user?.departmentId || '', degree: 'B.E.', currentYear: 4, graduationYear: 2027,
  cgpa: '', activeArrears: 0, arrearHistory: 0, skills: [], interests: [], preferredRoles: [], phone: '', portfolioUrl: '', resume: null,
})

// Same nine items the server counts.
const completion = computed(() => {
  const items = [form.phone, form.cgpa !== '', form.skills.length >= 3, form.interests.length >= 1, form.preferredRoles.length >= 1,
    form.resume, form.portfolioUrl, form.degree, form.studentCode]
  return Math.round((100 * items.filter(Boolean).length) / items.length)
})

function validate(i) {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (i === 0) {
    if (!/^[A-Za-z0-9-]{5,16}$/.test(form.studentCode)) errors.studentCode = '5–16 letters, digits or hyphens'
    if (!form.departmentId) errors.departmentId = 'Choose your department'
    if (!(form.currentYear >= 1 && form.currentYear <= 4)) errors.currentYear = 'Between 1 and 4'
    if (form.cgpa === '' || form.cgpa < 0 || form.cgpa > 10) errors.cgpa = 'Enter your CGPA (0–10)'
    if (!(form.activeArrears >= 0 && form.activeArrears <= 30)) errors.activeArrears = 'Between 0 and 30'
    if (!(form.arrearHistory >= 0 && form.arrearHistory <= 30)) errors.arrearHistory = 'Between 0 and 30'
  }
  if (i === 1) {
    if (form.skills.length < 3) errors.skills = 'Add at least 3 skills'
    if (form.preferredRoles.length < 1) errors.preferredRoles = 'Add at least one role'
  }
  if (i === 2) {
    if (form.portfolioUrl && !isUrl(form.portfolioUrl)) errors.portfolioUrl = 'Use a full link starting with http(s)://'
    if (form.phone && !/^\+?[0-9 ]{10,15}$/.test(form.phone)) errors.phone = 'Use 10–15 digits'
    if (form.resume && form.resume.size > 5 * 1024 * 1024) errors.resume = 'The file must be 5 MB or smaller'
    if (form.resume && !/\.(pdf|docx)$/i.test(form.resume.name)) errors.resume = 'Use a PDF or Word (.docx) file'
  }
  return !Object.keys(errors).length
}

function next() { if (validate(step.value)) step.value++ }

async function finish() {
  if (!validate(2)) return
  busy.value = true
  failure.value = ''
  let resumeFile = null
  try {
    if (form.resume) {
      const fd = new FormData()
      fd.append('file', form.resume)
      fd.append('title', 'Resume')
      fd.append('type', 'resume')
      resumeFile = (await documentsApi.upload(fd)).fileName
    }
    const { resume, ...body } = form
    await studentApi.onboarding({
      ...body, departmentId: Number(form.departmentId), cgpa: Number(form.cgpa), resumeFile,
      phone: form.phone || null, portfolioUrl: form.portfolioUrl || null,
    })
    await auth.reloadMe()
    toast.success('Welcome aboard! Your profile is ready.')
    router.replace('/student/dashboard')
  } catch (e) {
    if (applyServerErrors(errors, e) && (errors.studentCode || errors.cgpa)) step.value = 0
    failure.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-page px-4 py-10">
    <div class="mx-auto max-w-2xl">
      <div class="mb-6 flex items-center gap-3">
        <div class="flex size-10 items-center justify-center rounded-xl bg-navy-800 text-white"><GraduationCap class="size-6" /></div>
        <div>
          <h1 class="text-xl">Welcome, {{ auth.user?.name.split(' ')[0] }}</h1>
          <p class="text-sm text-muted">Set up your placement profile. It takes about two minutes.</p>
        </div>
      </div>

      <div class="card p-6">
        <div class="mb-1 flex justify-between text-xs text-muted"><span>Profile completion</span><span>{{ completion }}%</span></div>
        <div class="mb-6 h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full bg-brand-600 transition-all" :style="{ width: completion + '%' }" /></div>

        <ol class="mb-6 flex gap-2">
          <li v-for="(s, i) in steps" :key="s" class="flex flex-1 items-center gap-2 text-sm" :class="i <= step ? 'text-ink' : 'text-muted'">
            <span class="flex size-6 items-center justify-center rounded-full text-xs font-semibold" :class="i <= step ? 'bg-navy-800 text-white' : 'bg-slate-100'">{{ i + 1 }}</span>
            <span class="hidden sm:inline">{{ s }}</span>
          </li>
        </ol>

        <p v-if="failure" class="alert alert-error mb-4">{{ failure }}</p>

        <div v-if="step === 0" class="grid gap-4 sm:grid-cols-2">
          <FormField label="Student ID / roll number" :error="errors.studentCode" for="code" required>
            <input id="code" v-model.trim="form.studentCode" class="input" placeholder="23CSE101" />
          </FormField>
          <FormField label="Department" :error="errors.departmentId" for="dept" required>
            <select id="dept" v-model="form.departmentId" class="input">
              <option value="">Choose…</option>
              <option v-for="d in reference?.departments || []" :key="d.value" :value="d.value">{{ d.label }} — {{ d.name }}</option>
            </select>
          </FormField>
          <FormField label="Degree" for="deg" required>
            <select id="deg" v-model="form.degree" class="input"><option v-for="d in ['B.E.', 'B.Tech', 'M.E.', 'M.Tech', 'MBA', 'MCA']" :key="d">{{ d }}</option></select>
          </FormField>
          <FormField label="Current year" :error="errors.currentYear" for="cy" required>
            <select id="cy" v-model.number="form.currentYear" class="input"><option v-for="y in 4" :key="y" :value="y">Year {{ y }}</option></select>
          </FormField>
          <FormField label="Graduation year" for="gy" required>
            <select id="gy" v-model.number="form.graduationYear" class="input"><option v-for="y in [2026, 2027, 2028, 2029]" :key="y">{{ y }}</option></select>
          </FormField>
          <FormField label="CGPA" :error="errors.cgpa" hint="Verified later by the placement cell" for="cgpa" required>
            <input id="cgpa" v-model.number="form.cgpa" type="number" min="0" max="10" step="0.01" class="input" />
          </FormField>
          <FormField label="Active arrears" :error="errors.activeArrears" for="aa">
            <input id="aa" v-model.number="form.activeArrears" type="number" min="0" max="30" class="input" />
          </FormField>
          <FormField label="Arrear history" :error="errors.arrearHistory" for="ah">
            <input id="ah" v-model.number="form.arrearHistory" type="number" min="0" max="30" class="input" />
          </FormField>
        </div>

        <div v-else-if="step === 1" class="space-y-4">
          <FormField label="Skills" :error="errors.skills" hint="At least 3. Press Enter after each." required>
            <TagInput v-model="form.skills" :suggestions="SKILL_SUGGESTIONS" placeholder="e.g. Python" />
          </FormField>
          <FormField label="Interests"><TagInput v-model="form.interests" :suggestions="INTEREST_SUGGESTIONS" placeholder="e.g. Cloud" /></FormField>
          <FormField label="Preferred roles" :error="errors.preferredRoles" required>
            <TagInput v-model="form.preferredRoles" :suggestions="ROLE_SUGGESTIONS" placeholder="e.g. Software Engineer" />
          </FormField>
        </div>

        <div v-else class="space-y-4">
          <FormField label="Resume (optional)" :error="errors.resume" hint="PDF or Word (.docx), up to 5 MB" for="resume">
            <input id="resume" type="file" accept=".pdf,.docx" class="input" @change="form.resume = $event.target.files[0] || null" />
          </FormField>
          <FormField label="Phone (optional)" :error="errors.phone" for="phone"><input id="phone" v-model="form.phone" class="input" placeholder="+91 98765 43210" /></FormField>
          <FormField label="Portfolio / GitHub link (optional)" :error="errors.portfolioUrl" for="pf">
            <input id="pf" v-model="form.portfolioUrl" class="input" placeholder="https://github.com/you" />
          </FormField>
          <p class="alert alert-info">Your name, e-mail and placement status are managed by the placement cell. Your CGPA is marked unverified until they check it.</p>
        </div>

        <div class="mt-6 flex justify-between">
          <button class="btn btn-secondary" :disabled="step === 0 || busy" @click="step--">Back</button>
          <button v-if="step < 2" class="btn btn-primary" @click="next">Continue</button>
          <button v-else class="btn btn-primary" :disabled="busy" @click="finish"><Spinner v-if="busy" /> Finish setup</button>
        </div>
      </div>
      <button class="mt-4 text-sm text-muted hover:text-ink" @click="auth.logout().then(() => router.replace('/login'))">Sign out</button>
    </div>
  </div>
</template>
