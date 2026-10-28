<script setup>
// Upload a new document, or replace the file of an existing one (`replaceDoc`).
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from './ui/BaseDialog.vue'
import FormField from './ui/FormField.vue'
import Spinner from './ui/Spinner.vue'
import { documentsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'

const props = defineProps({ open: Boolean, replaceDoc: Object, defaultType: String })
const emit = defineEmits(['update:open', 'uploaded'])
const auth = useAuthStore()
const reference = useReference().ref
const isStudent = computed(() => auth.role === 'student')
const types = computed(() => (isStudent.value
  ? [{ value: 'resume', label: 'Resume' }, { value: 'certificate', label: 'Certificate' }]
  : [{ value: 'circular', label: 'Circular' }, { value: 'brochure', label: 'Company brochure' }, { value: 'eligibility', label: 'Eligibility document' }]))
const accept = computed(() => (isStudent.value || props.replaceDoc?.ownerStudentId ? '.pdf,.docx' : '.pdf'))

const form = reactive({ title: '', type: '', companyId: '', jobId: '', visibleToStudents: true, file: null })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const jobs = computed(() => (reference.value?.jobs || []).filter((j) => !form.companyId || j.companyId === form.companyId))

watch(() => props.open, (v) => {
  if (!v) return
  Object.assign(form, { title: '', type: props.defaultType || types.value[0].value, companyId: '', jobId: '', visibleToStudents: true, file: null })
  Object.keys(errors).forEach((k) => delete errors[k])
  failure.value = ''
})
watch(() => form.companyId, () => { if (form.jobId && !jobs.value.some((j) => j.value === form.jobId)) form.jobId = '' })

function pick(e) { form.file = e.target.files[0] || null }

async function submit() {
  errors.title = props.replaceDoc || (form.title.trim() && form.title.length <= 120) ? '' : 'Enter a title (up to 120 characters)'
  const ext = form.file?.name.split('.').pop().toLowerCase()
  errors.file = !form.file ? 'Choose a file'
    : !accept.value.split(',').includes('.' + ext) ? `Use a ${accept.value.replaceAll('.', '').toUpperCase().replace(',', ' or ')} file`
      : form.file.size > 5 * 1024 * 1024 ? 'The file must be 5 MB or smaller' : ''
  if (errors.title || errors.file) return
  const fd = new FormData()
  fd.append('file', form.file)
  busy.value = true
  failure.value = ''
  try {
    let doc
    if (props.replaceDoc) doc = await documentsApi.replace(props.replaceDoc.id, fd)
    else {
      fd.append('title', form.title.trim())
      fd.append('type', form.type)
      if (!isStudent.value) {
        if (form.companyId) fd.append('companyId', form.companyId)
        if (form.jobId) fd.append('jobId', form.jobId)
        fd.append('visibleToStudents', form.visibleToStudents ? 'true' : 'false')
      }
      doc = await documentsApi.upload(fd)
    }
    emit('uploaded', doc)
    emit('update:open', false)
  } catch (e) {
    failure.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog :open="open" :title="replaceDoc ? `Replace “${replaceDoc.title}”` : 'Upload document'" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="upload-form" class="space-y-4" novalidate @submit.prevent="submit">
      <p v-if="failure" class="alert alert-error">{{ failure }}</p>
      <p v-if="replaceDoc" class="alert alert-info">The new file becomes version {{ replaceDoc.version + 1 }}; its text is extracted again.</p>
      <template v-else>
        <FormField label="Title" :error="errors.title" for="doc-title" required>
          <input id="doc-title" v-model="form.title" class="input" maxlength="120" />
        </FormField>
        <FormField label="Type" for="doc-type">
          <select id="doc-type" v-model="form.type" class="input"><option v-for="t in types" :key="t.value" :value="t.value">{{ t.label }}</option></select>
        </FormField>
        <template v-if="!isStudent">
          <div class="grid gap-4 sm:grid-cols-2">
            <FormField label="Company (optional)" for="doc-company">
              <select id="doc-company" v-model="form.companyId" class="input">
                <option value="">None</option>
                <option v-for="c in reference?.companies || []" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
            </FormField>
            <FormField label="Job (optional)" for="doc-job">
              <select id="doc-job" v-model="form.jobId" class="input">
                <option value="">None</option>
                <option v-for="j in jobs" :key="j.value" :value="j.value">{{ j.label }}</option>
              </select>
            </FormField>
          </div>
          <label class="flex items-center gap-2 text-sm"><input v-model="form.visibleToStudents" type="checkbox" class="checkbox" /> Visible to students</label>
        </template>
      </template>
      <FormField label="File" :error="errors.file" :hint="`${accept.replaceAll('.', '').toUpperCase().replace(',', ' or ')}, up to 5 MB`" for="doc-file" required>
        <input id="doc-file" type="file" :accept="accept" class="input file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-2 file:py-1" @change="pick" />
      </FormField>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="upload-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> {{ replaceDoc ? 'Replace file' : 'Upload' }}</button>
    </template>
  </BaseDialog>
</template>
