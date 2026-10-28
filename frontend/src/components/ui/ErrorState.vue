<script setup>
import { computed } from 'vue'
import { AlertTriangle, Lock, SearchX, Wrench } from '@lucide/vue'

const props = defineProps({ error: { type: Object, required: true } })
const emit = defineEmits(['retry'])

const view = computed(() => {
  const s = props.error?.status
  if (s === 403) return { icon: Lock, title: 'Permission denied', text: props.error.message, retry: false }
  if (s === 404) return { icon: SearchX, title: 'Not found', text: props.error.message, retry: false }
  if (s === 501) return { icon: Wrench, title: 'Not available yet', text: props.error.message, retry: false }
  return { icon: AlertTriangle, title: 'Something went wrong', text: props.error?.message || 'Please try again.', retry: true }
})
</script>

<template>
  <div class="flex flex-col items-center px-6 py-10 text-center" role="alert">
    <div class="mb-3 flex size-12 items-center justify-center rounded-full bg-red-50 text-red-700">
      <component :is="view.icon" class="size-6" />
    </div>
    <p class="font-medium text-ink">{{ view.title }}</p>
    <p class="mt-1 max-w-md text-sm text-muted">{{ view.text }}</p>
    <button v-if="view.retry" class="btn btn-secondary mt-4" @click="emit('retry')">Try again</button>
  </div>
</template>
