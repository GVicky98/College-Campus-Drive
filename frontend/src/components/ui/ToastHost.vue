<script setup>
import { CheckCircle2, Info, TriangleAlert, XCircle } from '@lucide/vue'
import { toastState } from '@/composables/toast'
const icons = { success: CheckCircle2, error: XCircle, info: Info, warning: TriangleAlert }
const tones = { success: 'bg-green-700', error: 'bg-red-700', info: 'bg-navy-800', warning: 'bg-amber-600' }
</script>

<template>
  <Teleport to="body">
    <Transition enter-from-class="translate-y-4 opacity-0" leave-to-class="translate-y-4 opacity-0" enter-active-class="transition" leave-active-class="transition">
      <div v-if="toastState.visible" role="status" aria-live="polite"
        class="fixed bottom-5 left-1/2 z-[60] flex max-w-[92vw] -translate-x-1/2 items-center gap-2 rounded-xl px-4 py-3 text-sm text-white shadow-lg"
        :class="tones[toastState.tone]">
        <component :is="icons[toastState.tone]" class="size-4 shrink-0" />
        <span>{{ toastState.message }}</span>
        <button class="ml-2 text-white/80 hover:text-white" aria-label="Dismiss" @click="toastState.visible = false">✕</button>
      </div>
    </Transition>
  </Teleport>
</template>
