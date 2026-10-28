<script setup>
// Confirm an action. `action` is an async function; errors are shown inline and the dialog stays open.
import { ref, watch } from 'vue'
import BaseDialog from './BaseDialog.vue'
import Spinner from './Spinner.vue'

const props = defineProps({
  open: Boolean,
  title: { type: String, required: true },
  confirmLabel: { type: String, default: 'Confirm' },
  tone: { type: String, default: 'primary' }, // primary | danger | warning
  requireReason: Boolean,
  reasonLabel: { type: String, default: 'Reason' },
  minReason: { type: Number, default: 3 },
  action: { type: Function, default: async () => {} },
  disabled: Boolean,
})
const emit = defineEmits(['update:open', 'done'])
const busy = ref(false)
const error = ref('')
const reason = ref('')

watch(() => props.open, (v) => { if (v) { error.value = ''; reason.value = '' } })

async function run() {
  if (props.requireReason && reason.value.trim().length < props.minReason) {
    error.value = `Please give a reason (at least ${props.minReason} characters).`
    return
  }
  busy.value = true
  error.value = ''
  try {
    const result = await props.action(reason.value.trim())
    emit('update:open', false)
    emit('done', result)
  } catch (e) {
    error.value = e?.message || 'Something went wrong.'
  } finally {
    busy.value = false
  }
}
const btn = { primary: 'btn-primary', danger: 'btn-danger', warning: 'btn-warning' }
</script>

<template>
  <BaseDialog :open="open" :title="title" size="sm" :persistent="busy" @update:open="emit('update:open', $event)">
    <div class="space-y-3 text-sm text-slate-700">
      <slot />
      <div v-if="requireReason">
        <label class="label" for="confirm-reason">{{ reasonLabel }}</label>
        <textarea id="confirm-reason" v-model="reason" rows="3" class="input" maxlength="300" />
      </div>
      <p v-if="error" class="alert alert-error">{{ error }}</p>
    </div>
    <template #footer>
      <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
      <button class="btn" :class="btn[tone]" :disabled="busy || disabled" @click="run">
        <Spinner v-if="busy" /> {{ busy ? 'Working…' : confirmLabel }}
      </button>
    </template>
  </BaseDialog>
</template>
