<script setup>
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { adminApi } from '@/api'
import { useReference } from '@/composables/useReference'
import { applyServerErrors } from '@/utils/validation'
import { POLICY_KINDS } from './policyKinds'

const props = defineProps({ open: Boolean, policy: Object })
const emit = defineEmits(['update:open', 'saved'])
const reference = useReference().ref
const form = reactive({ name: '', description: '', kind: 'max_offers', scope: 'college', scopeValue: '', enabled: true, params: {} })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')
const kind = computed(() => POLICY_KINDS[form.kind])

watch(() => props.open, (v) => {
  if (!v) return
  const p = props.policy
  Object.assign(form, p
    ? { name: p.name, description: p.description, kind: p.kind, scope: p.scope, scopeValue: p.scopeValue || '', enabled: p.enabled, params: { ...p.params } }
    : { name: '', description: '', kind: 'max_offers', scope: 'college', scopeValue: '', enabled: true, params: { ...POLICY_KINDS.max_offers.defaults } })
  Object.keys(errors).forEach((k) => delete errors[k])
  failure.value = ''
})
watch(() => form.kind, (k) => { if (!props.policy) form.params = { ...POLICY_KINDS[k].defaults } })
watch(() => form.scope, () => { form.scopeValue = '' })

async function save() {
  errors.name = form.name.trim() ? '' : 'Name the policy'
  errors.scopeValue = form.scope !== 'college' && !form.scopeValue ? 'Choose what this applies to' : ''
  for (const f of kind.value.fields) {
    if (f.type === 'number' && !(Number.isInteger(Number(form.params[f.key])) && form.params[f.key] >= f.min && form.params[f.key] <= f.max))
      errors[f.key] = `A whole number from ${f.min} to ${f.max}`
    else errors[f.key] = ''
  }
  if (Object.values(errors).some(Boolean)) return
  busy.value = true
  failure.value = ''
  const params = Object.fromEntries(kind.value.fields.map((f) => [f.key, f.type === 'number' ? Number(form.params[f.key]) : Boolean(form.params[f.key])]))
  const body = { name: form.name.trim(), description: form.description.trim(), kind: form.kind, scope: form.scope,
    scopeValue: form.scope === 'college' ? null : String(form.scopeValue), params, enabled: form.enabled }
  try {
    const saved = props.policy ? await adminApi.updatePolicy(props.policy.id, body) : await adminApi.createPolicy(body)
    emit('saved', saved)
    emit('update:open', false)
  } catch (e) { applyServerErrors(errors, e); failure.value = e.message } finally { busy.value = false }
}
</script>

<template>
  <BaseDialog :open="open" :title="policy ? 'Edit policy' : 'Add policy'" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="policy-form" class="space-y-4" novalidate @submit.prevent="save">
      <p v-if="failure" class="alert alert-error">{{ failure }}</p>
      <FormField label="Name" :error="errors.name" for="p-name" required><input id="p-name" v-model="form.name" class="input" maxlength="160" /></FormField>
      <FormField label="Description" for="p-desc"><textarea id="p-desc" v-model="form.description" rows="2" class="input" maxlength="400" /></FormField>
      <FormField label="Type" :hint="policy ? 'The type cannot change after creation' : kind.help" for="p-kind">
        <select id="p-kind" v-model="form.kind" class="input" :disabled="!!policy">
          <option v-for="(k, key) in POLICY_KINDS" :key="key" :value="key">{{ k.label }}</option>
        </select>
      </FormField>
      <div class="grid gap-4 sm:grid-cols-2">
        <template v-for="f in kind.fields" :key="f.key">
          <FormField v-if="f.type === 'number'" :label="f.label" :error="errors[f.key]" :for="`p-${f.key}`">
            <input :id="`p-${f.key}`" v-model.number="form.params[f.key]" type="number" :min="f.min" :max="f.max" class="input" />
          </FormField>
          <label v-else class="flex items-center gap-2 text-sm sm:col-span-2"><input v-model="form.params[f.key]" type="checkbox" class="checkbox" /> {{ f.label }}</label>
        </template>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <FormField label="Applies to" for="p-scope">
          <select id="p-scope" v-model="form.scope" class="input"><option value="college">Whole college</option><option value="department">One department</option><option value="academic_year">One batch</option></select>
        </FormField>
        <FormField v-if="form.scope !== 'college'" :label="form.scope === 'department' ? 'Department' : 'Batch'" :error="errors.scopeValue" for="p-sv">
          <select id="p-sv" v-model="form.scopeValue" class="input">
            <option value="">Choose…</option>
            <template v-if="form.scope === 'department'"><option v-for="d in reference?.departments || []" :key="d.value" :value="d.value">{{ d.label }}</option></template>
            <template v-else><option v-for="y in reference?.graduationYears || []" :key="y.value" :value="y.value">{{ y.label }}</option></template>
          </select>
        </FormField>
      </div>
      <label class="flex items-center gap-2 text-sm"><input v-model="form.enabled" type="checkbox" class="checkbox" /> Enabled</label>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="policy-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Save policy</button>
    </template>
  </BaseDialog>
</template>
