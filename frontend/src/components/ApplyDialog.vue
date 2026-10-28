<script setup>
import { computed } from 'vue'
import ConfirmDialog from './ui/ConfirmDialog.vue'
import StatusChip from './ui/StatusChip.vue'
import { applicationsApi } from '@/api'
import { formatDateTime } from '@/utils/format'
import { useToast } from '@/composables/toast'

const props = defineProps({ open: Boolean, view: Object })
const emit = defineEmits(['update:open', 'applied'])
const toast = useToast()
const eligible = computed(() => props.view?.eligibility?.state === 'eligible')

async function apply() {
  const result = await applicationsApi.apply(props.view.job.id)
  toast.success(`Applied to ${props.view.company.name} — ${props.view.job.title}`)
  emit('applied', result)
}
</script>

<template>
  <ConfirmDialog v-if="view" :open="open" title="Confirm application" :confirm-label="eligible ? 'Submit application' : 'Not eligible'"
    :disabled="!eligible" :action="apply" @update:open="emit('update:open', $event)">
    <div class="rounded-xl border border-line p-3">
      <p class="font-medium">{{ view.job.title }}</p>
      <p class="text-muted">{{ view.company.name }} · {{ view.job.location }}</p>
      <p class="mt-1 text-xs text-muted">Apply by {{ formatDateTime(view.job.deadline) }}</p>
      <div class="mt-2"><StatusChip kind="eligibility" :value="view.eligibility?.state" /></div>
    </div>
    <p v-if="eligible" class="alert alert-info">A snapshot of your profile and eligibility is saved with the application.</p>
    <p v-else class="alert alert-error">{{ view.eligibility?.summary }}</p>
  </ConfirmDialog>
</template>
