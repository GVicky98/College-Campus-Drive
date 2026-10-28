<script setup>
// Runs one lifecycle action (publish / close / cancel / archive ...) after confirmation.
import { computed } from 'vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { jobsApi } from '@/api'
import { useToast } from '@/composables/toast'
import { ACTION_INFO } from './jobActions'

const props = defineProps({ open: Boolean, job: Object, action: String })
const emit = defineEmits(['update:open', 'done'])
const toast = useToast()
const info = computed(() => ACTION_INFO[props.action] || {})
const STATUS = { publish: 'published', unpublish: 'draft', close: 'closed', reopen: 'published', cancel: 'cancelled' }

async function run(reason) {
  const a = props.action
  const job = a === 'archive' || a === 'restore'
    ? await jobsApi.archive(props.job.id, a === 'archive')
    : await jobsApi.setStatus(props.job.id, STATUS[a], reason || undefined)
  toast.success(`${props.job.title}: ${info.value.label.toLowerCase()} done`)
  emit('done', job)
}
</script>

<template>
  <ConfirmDialog v-if="job && action" :open="open" :title="info.title" :confirm-label="info.label" :tone="info.tone"
    :require-reason="info.reason" reason-label="Reason (sent to applicants)" :action="run" @update:open="emit('update:open', $event)">
    <p><b>{{ job.title }}</b></p>
    <p>{{ info.text }}</p>
  </ConfirmDialog>
</template>
