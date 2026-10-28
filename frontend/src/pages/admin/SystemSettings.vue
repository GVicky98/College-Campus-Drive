<script setup>
import { computed, reactive, ref } from 'vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import FormField from '@/components/ui/FormField.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Forbidden from '@/pages/auth/Forbidden.vue'
import { adminApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/toast'
import { usePublicSettings } from '@/composables/usePublicSettings'
import { applyServerErrors, isEmail } from '@/utils/validation'

const auth = useAuthStore()
const toast = useToast()
const publicSettings = usePublicSettings()
const form = reactive({})
const errors = reactive({})
const saving = ref(false)
const failure = ref('')
const { data, loading, error, reload } = useAsync(async () => {
  const r = await adminApi.settings()
  Object.assign(form, r.settings)
  return r
}, { immediate: auth.role === 'admin' })
const dirty = computed(() => data.value && JSON.stringify(form) !== JSON.stringify(data.value.settings))

async function save() {
  errors.collegeName = form.collegeName?.trim() ? '' : 'Enter the college name'
  errors.placementEmail = isEmail(form.placementEmail) ? '' : 'Enter a valid e-mail'
  errors.sessionTimeoutMinutes = form.sessionTimeoutMinutes >= 5 && form.sessionTimeoutMinutes <= 1440 ? '' : 'Between 5 and 1440 minutes'
  errors.maintenanceMessage = form.maintenanceBanner && !form.maintenanceMessage?.trim() ? 'Write the message to show' : ''
  if (Object.values(errors).some(Boolean)) return
  saving.value = true
  failure.value = ''
  try {
    data.value = await adminApi.saveSettings({ ...form, sessionTimeoutMinutes: Number(form.sessionTimeoutMinutes) })
    Object.assign(form, data.value.settings)
    publicSettings.reload()
    toast.success('Settings saved')
  } catch (e) { applyServerErrors(errors, e); failure.value = e.message } finally { saving.value = false }
}
</script>

<template>
  <Forbidden v-if="auth.role !== 'admin'" embedded />
  <template v-else>
    <PageHeader title="System settings" subtitle="College-wide settings. Changes are recorded in the audit log.">
      <template #actions>
        <button class="btn btn-secondary" :disabled="!dirty || saving" @click="Object.assign(form, data.settings)">Discard changes</button>
        <button class="btn btn-primary" :disabled="!dirty || saving" @click="save"><Spinner v-if="saving" /> Save settings</button>
      </template>
    </PageHeader>
    <AsyncBlock :loading="loading" :error="error" :has-data="!!data" @retry="reload">
      <div v-if="data" class="grid gap-6 lg:grid-cols-3">
        <div class="space-y-6 lg:col-span-2">
          <p v-if="failure" class="alert alert-error">{{ failure }}</p>
          <SectionCard title="College">
            <div class="grid gap-4 sm:grid-cols-2">
              <FormField label="College name" :error="errors.collegeName" hint="Shown on the sign-in page and in the sidebar" for="s-name" required>
                <input id="s-name" v-model="form.collegeName" class="input" maxlength="160" /></FormField>
              <FormField label="Placement office e-mail" :error="errors.placementEmail" for="s-mail" required>
                <input id="s-mail" v-model="form.placementEmail" type="email" class="input" /></FormField>
              <FormField label="Placement season" hint="A label such as 2026-27" for="s-season"><input id="s-season" v-model="form.placementSeason" class="input" maxlength="40" /></FormField>
              <FormField label="Current academic year" hint="Change it under Departments & courses">
                <p class="input bg-slate-50">{{ data.status.activeYear || 'None set' }} <RouterLink to="/admin/departments" class="link ml-2 text-xs">Change</RouterLink></p>
              </FormField>
            </div>
          </SectionCard>
          <SectionCard title="Sessions">
            <FormField label="Sign out after inactivity (minutes)" :error="errors.sessionTimeoutMinutes" hint="Users who are idle this long are signed out of the browser. 5–1440." for="s-timeout">
              <input id="s-timeout" v-model.number="form.sessionTimeoutMinutes" type="number" min="5" max="1440" class="input w-40" /></FormField>
          </SectionCard>
          <SectionCard title="Maintenance banner">
            <label class="flex items-center gap-2 text-sm"><input v-model="form.maintenanceBanner" type="checkbox" class="checkbox" /> Show a banner to every signed-in user</label>
            <FormField class="mt-3" label="Message" :error="errors.maintenanceMessage" for="s-msg">
              <input id="s-msg" v-model="form.maintenanceMessage" class="input" maxlength="300" placeholder="The portal will be down for maintenance on Saturday 6–8 pm." /></FormField>
          </SectionCard>
        </div>
        <SectionCard title="System status">
          <dl class="space-y-4 text-sm">
            <div><dt class="text-xs text-muted">AI assistant</dt>
              <dd class="mt-1 flex flex-wrap items-center gap-2"><StatusChip :tone="data.status.assistant.available ? 'success' : 'warning'" :label="data.status.assistant.available ? 'Configured' : 'Not configured'" />
                <span class="text-muted">{{ data.status.assistant.provider }}<span v-if="data.status.assistant.model"> · {{ data.status.assistant.model }}</span></span></dd>
              <p v-if="!data.status.assistant.available" class="hint">Set LLM_PROVIDER and LLM_API_KEY in backend/.env and restart the server. Keys are never stored here.</p></div>
            <div><dt class="text-xs text-muted">Documents searchable by the assistant</dt><dd>{{ data.status.documents.indexed }}</dd></div>
            <div><dt class="text-xs text-muted">Documents with no readable text</dt><dd>{{ data.status.documents.failed }}</dd></div>
          </dl>
        </SectionCard>
      </div>
    </AsyncBlock>
  </template>
</template>
