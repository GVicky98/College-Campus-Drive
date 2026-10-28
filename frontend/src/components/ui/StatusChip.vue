<script setup>
// One coloured chip for every status in the app. Pass `kind` + `value`, or a raw `tone` + `label`.
import { computed } from 'vue'
import { sentenceCase } from '@/utils/format'

const props = defineProps({ kind: String, value: String, tone: String, label: String })

const MAP = {
  application: { applied: 'info', shortlisted: 'purple', interview: 'warning', selected: 'success', offer_received: 'success', rejected: 'error', withdrawn: 'neutral' },
  offer: { pending: 'neutral', received: 'info', accepted: 'success', declined: 'neutral', withdrawn: 'error' },
  job: { draft: 'neutral', published: 'success', closed: 'warning', cancelled: 'error' },
  interview: { scheduled: 'info', completed: 'success', cancelled: 'error', no_show: 'warning' },
  processing: { queued: 'neutral', processing: 'info', indexed: 'success', failed: 'error' },
  eligibility: { eligible: 'success', not_eligible: 'error', profile_incomplete: 'warning', needs_verification: 'info' },
  tier: { regular: 'neutral', dream: 'info', super_dream: 'purple' },
  placement: { unplaced: 'neutral', in_process: 'info', placed: 'success', opted_out: 'warning' },
  user: { active: 'success', inactive: 'neutral', invited: 'info' },
  result: { success: 'success', denied: 'error', failed: 'warning' },
  role: { admin: 'purple', faculty: 'info', student: 'neutral' },
  reminder: { drive: 'info', deadline: 'warning', interview: 'purple', custom: 'neutral' },
  notification: { drive: 'info', deadline: 'warning', interview: 'purple', offer: 'success', application: 'info', system: 'neutral' },
}
const LABELS = {
  offer_received: 'Offer received', no_show: 'No-show', not_eligible: 'Not eligible', profile_incomplete: 'Profile incomplete',
  needs_verification: 'Needs verification', super_dream: 'Super Dream', in_process: 'In process', opted_out: 'Opted out',
  indexed: 'Ready', custom: 'Personal', drive: 'Placement drive', deadline: 'Deadline',
}
const TONES = {
  success: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  error: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  purple: 'bg-violet-100 text-violet-800',
  neutral: 'bg-slate-100 text-slate-700',
}
const tone = computed(() => props.tone || MAP[props.kind]?.[props.value] || 'neutral')
const text = computed(() => props.label || LABELS[props.value] || sentenceCase(props.value || ''))
</script>

<template>
  <span class="inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium" :class="TONES[tone]">
    <slot>{{ text }}</slot>
  </span>
</template>
