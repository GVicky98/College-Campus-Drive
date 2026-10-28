<script setup>
// The six notification switches. `instant` saves each toggle at once; otherwise changes wait for "Save".
import { computed, ref } from 'vue'
import AsyncBlock from './ui/AsyncBlock.vue'
import Spinner from './ui/Spinner.vue'
import { notificationsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useToast } from '@/composables/toast'

const props = defineProps({ instant: Boolean })
const toast = useToast()
const draft = ref(null)
const { data, loading, error, reload } = useAsync(async () => {
  const p = await notificationsApi.preferences()
  draft.value = { ...p }
  return p
})
const saving = ref(false)
const dirty = computed(() => data.value && JSON.stringify(data.value) !== JSON.stringify(draft.value))

const ITEMS = [
  ['driveReminders', 'Placement drive reminders', 'When a drive you applied to is coming up.'],
  ['deadlineReminders', 'Deadline reminders', 'Before application deadlines close.'],
  ['interviewAlerts', 'Interview alerts', 'When interviews are scheduled, changed or cancelled.'],
  ['offerUpdates', 'Offer updates', 'When an offer is issued or changes.'],
  ['email', 'E-mail copies', 'Saved as your preference; e-mail delivery is not set up on this server yet.'],
  ['push', 'Browser push', 'Saved as your preference; push delivery is not set up on this server yet.'],
]

async function save(next = draft.value) {
  saving.value = true
  const before = { ...data.value }
  try {
    data.value = await notificationsApi.savePreferences(next)
    draft.value = { ...data.value }
    if (!props.instant) toast.success('Preferences saved')
  } catch (e) {
    draft.value = before
    toast.error(e.message)
  } finally { saving.value = false }
}
function toggle(key) {
  draft.value[key] = !draft.value[key]
  if (props.instant) save({ ...draft.value })
}
</script>

<template>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!draft" @retry="reload">
    <ul v-if="draft" class="divide-y divide-line">
      <li v-for="[key, label, hint] in ITEMS" :key="key" class="flex items-center justify-between gap-4 py-3">
        <div><p class="text-sm font-medium">{{ label }}</p><p class="text-xs text-muted">{{ hint }}</p></div>
        <button role="switch" :aria-checked="draft[key]" :aria-label="label" :disabled="saving"
          class="relative h-6 w-11 shrink-0 rounded-full transition" :class="draft[key] ? 'bg-brand-600' : 'bg-slate-300'" @click="toggle(key)">
          <span class="absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition" :class="draft[key] && 'translate-x-5'" />
        </button>
      </li>
    </ul>
    <div v-if="!instant && draft" class="mt-4 flex justify-end gap-2">
      <button class="btn btn-secondary" :disabled="!dirty || saving" @click="draft = { ...data }">Discard</button>
      <button class="btn btn-primary" :disabled="!dirty || saving" @click="save()"><Spinner v-if="saving" /> Save</button>
    </div>
  </AsyncBlock>
</template>
