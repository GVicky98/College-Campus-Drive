<script setup>
// One dialog for departments, courses and academic years (`kind`).
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { adminApi } from '@/api'
import { applyServerErrors } from '@/utils/validation'

const props = defineProps({ open: Boolean, kind: String, item: Object, departments: { type: Array, default: () => [] } })
const emit = defineEmits(['update:open', 'saved'])
const form = reactive({})
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const NOUN = { department: 'department', course: 'programme', year: 'academic year' }
const title = computed(() => `${props.item ? 'Edit' : 'Add'} ${NOUN[props.kind]}`)

watch(() => props.open, (v) => {
  if (!v) return
  Object.keys(form).forEach((k) => delete form[k])
  Object.keys(errors).forEach((k) => delete errors[k])
  failure.value = ''
  const i = props.item || {}
  if (props.kind === 'department') Object.assign(form, { code: i.code || '', name: i.name || '', headName: i.headName || '' })
  if (props.kind === 'course') Object.assign(form, { code: i.code || '', name: i.name || '', degree: i.degree || 'B.E.', departmentId: i.departmentId || '', durationYears: i.durationYears || 4 })
  if (props.kind === 'year') Object.assign(form, { label: i.label || '', graduationYear: i.graduationYear || '', active: i.active || false })
})

function validate() {
  if (props.kind !== 'year') {
    errors.code = /^[A-Za-z0-9&-]+$/.test(form.code || '') ? '' : 'Letters, digits, & and - only'
    errors.name = form.name?.trim() ? '' : 'Enter the name'
  }
  if (props.kind === 'course') {
    errors.departmentId = form.departmentId ? '' : 'Choose a department'
    errors.durationYears = form.durationYears >= 1 && form.durationYears <= 6 ? '' : 'Between 1 and 6'
  }
  if (props.kind === 'year') {
    errors.label = /^\d{4}-\d{2}$/.test(form.label) ? '' : 'Use the form 2026-27'
    errors.graduationYear = form.graduationYear >= 2000 && form.graduationYear <= 2100 ? '' : 'Enter the graduation year'
  }
  return !Object.values(errors).some(Boolean)
}
async function save() {
  if (!validate()) return
  busy.value = true
  failure.value = ''
  const id = props.item?.id
  try {
    if (props.kind === 'department') await adminApi.saveDepartment(id, { code: form.code.trim(), name: form.name.trim(), headName: form.headName.trim() || null })
    if (props.kind === 'course') await adminApi.saveCourse(id, { ...form, code: form.code.trim(), name: form.name.trim(), departmentId: Number(form.departmentId), durationYears: Number(form.durationYears) })
    if (props.kind === 'year') await adminApi.saveYear(id, { label: form.label, graduationYear: Number(form.graduationYear), active: form.active })
    emit('saved')
    emit('update:open', false)
  } catch (e) { applyServerErrors(errors, e); failure.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <BaseDialog :open="open" :title="title" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="acad-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="save">
      <p v-if="failure" class="alert alert-error sm:col-span-2">{{ failure }}</p>
      <template v-if="kind !== 'year'">
        <FormField label="Code" :error="errors.code" for="a-code" required><input id="a-code" v-model="form.code" class="input uppercase" :maxlength="kind === 'course' ? 24 : 16" /></FormField>
        <FormField label="Name" :error="errors.name" for="a-name" required><input id="a-name" v-model="form.name" class="input" maxlength="160" /></FormField>
      </template>
      <FormField v-if="kind === 'department'" class="sm:col-span-2" label="Head of department" for="a-head"><input id="a-head" v-model="form.headName" class="input" maxlength="120" /></FormField>
      <template v-if="kind === 'course'">
        <FormField label="Degree" for="a-deg"><select id="a-deg" v-model="form.degree" class="input"><option v-for="d in ['B.E.', 'B.Tech', 'M.E.', 'M.Tech', 'MBA', 'MCA']" :key="d">{{ d }}</option></select></FormField>
        <FormField label="Department" :error="errors.departmentId" for="a-dept" required>
          <select id="a-dept" v-model="form.departmentId" class="input"><option value="">Choose…</option><option v-for="d in departments" :key="d.id" :value="d.id">{{ d.code }} — {{ d.name }}</option></select>
        </FormField>
        <FormField label="Duration (years)" :error="errors.durationYears" for="a-dur"><input id="a-dur" v-model.number="form.durationYears" type="number" min="1" max="6" class="input" /></FormField>
      </template>
      <template v-if="kind === 'year'">
        <FormField label="Academic year" :error="errors.label" hint="e.g. 2026-27" for="a-label" required><input id="a-label" v-model="form.label" class="input" placeholder="2026-27" /></FormField>
        <FormField label="Graduation batch" :error="errors.graduationYear" for="a-grad" required><input id="a-grad" v-model.number="form.graduationYear" type="number" class="input" /></FormField>
        <label class="flex items-center gap-2 text-sm sm:col-span-2"><input v-model="form.active" type="checkbox" class="checkbox" :disabled="item?.active" />
          Current academic year (the previous current year is switched off)</label>
      </template>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="acad-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Save</button>
    </template>
  </BaseDialog>
</template>
