<script setup>
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { usersApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'
import { applyServerErrors, isEmail } from '@/utils/validation'

const props = defineProps({ open: Boolean, user: Object })
const emit = defineEmits(['update:open', 'saved'])
const auth = useAuthStore()
const reference = useReference().ref
const form = reactive({ name: '', email: '', userCode: '', role: 'faculty', departmentId: '', graduationYear: '' })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const editing = computed(() => Boolean(props.user))
// Students can't become staff (and back); only administrators may create administrators.
const roles = computed(() => {
  if (editing.value && props.user.role === 'student') return ['student']
  const r = editing.value ? ['faculty', 'admin'] : ['student', 'faculty', 'admin']
  return auth.role === 'admin' ? r : r.filter((x) => x !== 'admin')
})

watch(() => props.open, (v) => {
  if (!v) return
  const u = props.user
  Object.assign(form, u
    ? { name: u.name, email: u.email, userCode: u.userCode, role: u.role, departmentId: u.departmentId || '', graduationYear: u.graduationYear || '' }
    : { name: '', email: '', userCode: '', role: 'faculty', departmentId: '', graduationYear: '' })
  Object.keys(errors).forEach((k) => delete errors[k])
  failure.value = ''
})

async function save() {
  errors.name = form.name.trim() ? '' : 'Enter the full name'
  errors.email = isEmail(form.email) ? '' : 'Enter a valid college e-mail'
  errors.userCode = /^[A-Za-z0-9][A-Za-z0-9._\-/]{0,31}$/.test(form.userCode) ? '' : 'Letters, digits and . _ - / (up to 32)'
  errors.departmentId = ['faculty', 'student'].includes(form.role) && !form.departmentId ? 'Choose a department' : ''
  if (Object.values(errors).some(Boolean)) return
  busy.value = true
  failure.value = ''
  const body = { name: form.name.trim(), email: form.email.trim(), userCode: form.userCode.trim(), role: form.role,
    departmentId: form.departmentId ? Number(form.departmentId) : null,
    graduationYear: form.role === 'student' && form.graduationYear ? Number(form.graduationYear) : null }
  try {
    const saved = editing.value ? await usersApi.update(props.user.id, body) : await usersApi.create(body)
    emit('saved', saved)
    emit('update:open', false)
  } catch (e) { applyServerErrors(errors, e); failure.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <BaseDialog :open="open" :title="editing ? `Edit ${user.name}` : 'Add user'" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="user-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="save">
      <p v-if="failure" class="alert alert-error sm:col-span-2">{{ failure }}</p>
      <p v-if="!editing" class="alert alert-info sm:col-span-2">The account is created as <b>invited</b>. A one-time link lets the person choose a password. E-mail is not set up on this server, so the link appears in the server log.</p>
      <FormField class="sm:col-span-2" label="Full name" :error="errors.name" for="u-name" required><input id="u-name" v-model="form.name" class="input" maxlength="120" /></FormField>
      <FormField label="College e-mail" :error="errors.email" for="u-email" required><input id="u-email" v-model="form.email" type="email" class="input" /></FormField>
      <FormField label="User ID / roll number" :error="errors.userCode" for="u-code" required><input id="u-code" v-model="form.userCode" class="input" maxlength="32" /></FormField>
      <FormField label="Role" for="u-role">
        <select id="u-role" v-model="form.role" class="input" :disabled="roles.length === 1">
          <option v-for="r in roles" :key="r" :value="r">{{ r[0].toUpperCase() + r.slice(1) }}</option>
        </select>
      </FormField>
      <FormField :label="form.role === 'faculty' ? 'Department scope' : 'Department'" :error="errors.departmentId" for="u-dept" :required="form.role !== 'admin'">
        <select id="u-dept" v-model="form.departmentId" class="input">
          <option value="">{{ form.role === 'admin' ? 'None' : 'Choose…' }}</option>
          <option v-for="d in reference?.departments || []" :key="d.value" :value="d.value">{{ d.label }} — {{ d.name }}</option>
        </select>
      </FormField>
      <FormField v-if="form.role === 'student'" label="Graduation batch" hint="Defaults to the current academic year" for="u-year">
        <select id="u-year" v-model="form.graduationYear" class="input">
          <option value="">Current year</option>
          <option v-for="y in reference?.graduationYears || []" :key="y.value" :value="y.value">{{ y.label }}</option>
        </select>
      </FormField>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="user-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> {{ editing ? 'Save changes' : 'Create user' }}</button>
    </template>
  </BaseDialog>
</template>
