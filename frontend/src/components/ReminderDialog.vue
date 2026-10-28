<script setup>
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from './ui/BaseDialog.vue'
import FormField from './ui/FormField.vue'
import Spinner from './ui/Spinner.vue'
import { jobsApi, remindersApi } from '@/api'
import { toLocalDateInput } from '@/utils/format'

const props = defineProps({ open: Boolean, reminder: Object }) // reminder = { reminder, ... } when editing
const emit = defineEmits(['update:open', 'saved'])
const form = reactive({ title: '', date: '', time: '09:00', jobId: '', kind: '' })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const jobs = ref([])
const editing = computed(() => Boolean(props.reminder))

watch(() => props.open, async (v) => {
  if (!v) return
  failure.value = ''
  Object.keys(errors).forEach((k) => delete errors[k])
  const r = props.reminder?.reminder
  if (r) {
    const d = new Date(r.at)
    Object.assign(form, { title: r.title, date: toLocalDateInput(d), time: d.toTimeString().slice(0, 5), jobId: r.jobId || '', kind: r.kind })
  } else Object.assign(form, { title: '', date: '', time: '09:00', jobId: '', kind: '' })
  if (!jobs.value.length) jobs.value = (await jobsApi.list({ pageSize: 50 }).catch(() => ({ items: [] }))).items
})

async function save() {
  errors.title = form.title.trim() ? (form.title.length > 140 ? 'At most 140 characters' : '') : 'Describe the reminder'
  errors.date = form.date ? '' : 'Pick a date'
  errors.time = form.time ? '' : 'Pick a time'
  const at = form.date && form.time ? new Date(`${form.date}T${form.time}`) : null
  if (!errors.date && !editing.value && at < new Date()) errors.date = 'Choose a time in the future'
  if (Object.values(errors).some(Boolean)) return
  busy.value = true
  failure.value = ''
  const body = { title: form.title.trim(), at: at.toISOString(), jobId: form.jobId ? Number(form.jobId) : null, kind: form.kind || null }
  try {
    const saved = editing.value ? await remindersApi.update(props.reminder.reminder.id, body) : await remindersApi.create(body)
    emit('saved', saved)
    emit('update:open', false)
  } catch (e) { failure.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <BaseDialog :open="open" :title="editing ? 'Edit reminder' : 'New reminder'" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="reminder-form" class="space-y-4" novalidate @submit.prevent="save">
      <p v-if="failure" class="alert alert-error">{{ failure }}</p>
      <FormField label="Description" :error="errors.title" :hint="`${form.title.length}/140`" for="r-title" required>
        <textarea id="r-title" v-model="form.title" rows="2" maxlength="140" class="input" />
      </FormField>
      <div class="grid grid-cols-2 gap-4">
        <FormField label="Date" :error="errors.date" for="r-date" required><input id="r-date" v-model="form.date" type="date" class="input" /></FormField>
        <FormField label="Time" :error="errors.time" for="r-time" required><input id="r-time" v-model="form.time" type="time" class="input" /></FormField>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <FormField label="Related drive (optional)" for="r-job">
          <select id="r-job" v-model="form.jobId" class="input">
            <option value="">None</option>
            <option v-for="v in jobs" :key="v.job.id" :value="v.job.id">{{ v.company.name }} — {{ v.job.title }}</option>
          </select>
        </FormField>
        <FormField label="Type" for="r-kind">
          <select id="r-kind" v-model="form.kind" class="input">
            <option value="">Automatic</option><option value="drive">Placement drive</option><option value="deadline">Application deadline</option>
            <option value="interview">Interview</option><option value="custom">Personal</option>
          </select>
        </FormField>
      </div>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="reminder-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Save reminder</button>
    </template>
  </BaseDialog>
</template>
