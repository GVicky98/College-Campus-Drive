<script setup>
import { reactive, ref, watch } from 'vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { companiesApi } from '@/api'
import { applyServerErrors, isEmail, isUrl } from '@/utils/validation'

const props = defineProps({ open: Boolean, company: Object })
const emit = defineEmits(['update:open', 'saved'])
const blank = { name: '', website: '', industry: '', tier: 'regular', description: '', contactName: '', contactEmail: '', contactPhone: '' }
const form = reactive({ ...blank })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')

watch(() => props.open, (v) => {
  if (!v) return
  Object.assign(form, blank, props.company ? Object.fromEntries(Object.keys(blank).map((k) => [k, props.company[k] ?? ''])) : {})
  Object.keys(errors).forEach((k) => delete errors[k])
  failure.value = ''
})

async function save() {
  errors.name = form.name.trim() ? '' : 'Enter the company name'
  errors.website = isUrl(form.website) ? '' : 'Enter the full website, e.g. https://example.com'
  errors.industry = form.industry.trim() ? '' : 'Enter the industry'
  errors.description = form.description.trim() ? '' : 'Add a short description'
  errors.contactName = form.contactName.trim() ? '' : 'Enter a contact person'
  errors.contactEmail = isEmail(form.contactEmail) ? '' : 'Enter a valid e-mail'
  if (Object.values(errors).some(Boolean)) return
  busy.value = true
  failure.value = ''
  const body = { ...form, contactPhone: form.contactPhone || null }
  try {
    const saved = props.company ? await companiesApi.update(props.company.id, body) : await companiesApi.create(body)
    emit('saved', saved)
    emit('update:open', false)
  } catch (e) {
    if (e.status === 409) errors.name = 'A company with this name already exists'
    applyServerErrors(errors, e)
    failure.value = e.message
  } finally { busy.value = false }
}
</script>

<template>
  <BaseDialog :open="open" :title="company ? `Edit ${company.name}` : 'Add company'" size="lg" :persistent="busy" @update:open="emit('update:open', $event)">
    <form id="company-form" class="grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="save">
      <p v-if="failure" class="alert alert-error sm:col-span-2">{{ failure }}</p>
      <FormField label="Company name" :error="errors.name" for="c-name" required><input id="c-name" v-model="form.name" class="input" maxlength="160" /></FormField>
      <FormField label="Website" :error="errors.website" for="c-web" required><input id="c-web" v-model="form.website" class="input" placeholder="https://" /></FormField>
      <FormField label="Industry" :error="errors.industry" for="c-ind" required><input id="c-ind" v-model="form.industry" class="input" /></FormField>
      <FormField label="Tier" for="c-tier">
        <select id="c-tier" v-model="form.tier" class="input"><option value="regular">Regular</option><option value="dream">Dream</option><option value="super_dream">Super Dream</option></select>
      </FormField>
      <FormField class="sm:col-span-2" label="Description" :error="errors.description" for="c-desc" required>
        <textarea id="c-desc" v-model="form.description" rows="3" class="input" maxlength="4000" />
      </FormField>
      <FormField label="Contact person" :error="errors.contactName" for="c-cn" required><input id="c-cn" v-model="form.contactName" class="input" /></FormField>
      <FormField label="Contact e-mail" :error="errors.contactEmail" for="c-ce" required><input id="c-ce" v-model="form.contactEmail" type="email" class="input" /></FormField>
      <FormField label="Contact phone (optional)" for="c-cp"><input id="c-cp" v-model="form.contactPhone" class="input" /></FormField>
    </form>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button type="submit" form="company-form" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Save company</button>
    </template>
  </BaseDialog>
</template>
