<script setup>
// A change the assistant prepared. Nothing happens until the user confirms; the server re-checks everything then.
import { ref } from 'vue'
import { TriangleAlert } from '@lucide/vue'
import Spinner from '../ui/Spinner.vue'
import { assistantApi } from '@/api'

const props = defineProps({ action: { type: Object, required: true } })
const emit = defineEmits(['changed'])
const busy = ref('')
const error = ref('')
const RESULT = { confirmed: 'alert-success', failed: 'alert-error', expired: 'alert-warning', cancelled: 'alert-info' }

async function run(kind) {
  busy.value = kind
  error.value = ''
  try {
    await (kind === 'confirm' ? assistantApi.confirm(props.action.id) : assistantApi.reject(props.action.id))
    emit('changed')
  } catch (e) { error.value = e.message; emit('changed') } finally { busy.value = '' }
}
</script>

<template>
  <div class="rounded-xl border p-3" :class="action.destructive ? 'border-red-200 bg-red-50/60' : 'border-brand-100 bg-brand-50/50'">
    <p class="font-semibold">{{ action.title }}</p>
    <p v-if="action.description" class="text-xs text-muted">{{ action.description }}</p>
    <dl v-if="action.details.length" class="mt-2 space-y-1 text-sm">
      <div v-for="d in action.details" :key="d.label + d.value" class="flex flex-wrap gap-x-2"><dt class="text-muted">{{ d.label }}:</dt><dd>{{ d.value }}</dd></div>
    </dl>
    <template v-if="action.state === 'awaiting_confirmation'">
      <p v-if="action.destructive" class="mt-2 flex items-center gap-1.5 text-xs text-red-800"><TriangleAlert class="size-3.5" /> This removes access or data. Check the details carefully.</p>
      <p class="mt-2 text-xs text-muted">Nothing happens until you confirm. The server checks the rules again first.</p>
      <p v-if="error" class="alert alert-error mt-2">{{ error }}</p>
      <div class="mt-3 flex gap-2">
        <button class="btn btn-sm" :class="action.destructive ? 'btn-danger' : 'btn-primary'" :disabled="!!busy" @click="run('confirm')">
          <Spinner v-if="busy === 'confirm'" /> {{ busy === 'confirm' ? 'Working…' : 'Confirm' }}</button>
        <button class="btn btn-secondary btn-sm" :disabled="!!busy" @click="run('reject')">Cancel</button>
      </div>
    </template>
    <p v-else class="alert mt-2" :class="RESULT[action.state]">{{ action.resultMessage || action.state }}</p>
  </div>
</template>
