<script setup>
import { Inbox } from '@lucide/vue'
defineProps({ title: { type: String, default: 'Nothing here yet' }, message: String, icon: { type: [Object, Function], default: () => Inbox } })
</script>

<template>
  <div class="flex flex-col items-center px-6 py-10 text-center">
    <div class="mb-3 flex size-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
      <component :is="icon" class="size-6" />
    </div>
    <p class="font-medium text-ink">{{ title }}</p>
    <p v-if="message" class="mt-1 max-w-md text-sm text-muted">{{ message }}</p>
    <div v-if="$slots.default" class="mt-4"><slot /></div>
  </div>
</template>
