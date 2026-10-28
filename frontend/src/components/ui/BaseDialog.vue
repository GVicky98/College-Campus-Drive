<script setup>
// Accessible modal dialog. v-model:open controls visibility; Esc and the backdrop close it unless `persistent`.
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({
  open: Boolean,
  title: String,
  size: { type: String, default: 'md' }, // sm | md | lg | xl
  persistent: Boolean,
})
const emit = defineEmits(['update:open', 'close'])
const panel = ref(null)
const widths = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' }

function close() {
  if (props.persistent) return
  emit('update:open', false)
  emit('close')
}
function onKey(e) { if (e.key === 'Escape' && props.open) close() }

watch(() => props.open, async (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) { await nextTick(); panel.value?.querySelector('input, select, textarea, button:not([data-close])')?.focus() }
})
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' })
</script>

<template>
  <Teleport to="body">
    <Transition enter-from-class="opacity-0" leave-to-class="opacity-0" enter-active-class="transition" leave-active-class="transition">
      <div v-if="open" class="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-0 sm:items-center sm:p-4" @mousedown.self="close">
        <div ref="panel" role="dialog" aria-modal="true" :aria-label="title"
          class="flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-white shadow-xl sm:rounded-2xl" :class="widths[size]">
          <div class="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
            <h2 class="text-base">{{ title }}</h2>
            <button data-close class="btn-icon" aria-label="Close" :disabled="persistent" @click="close"><X class="size-4" /></button>
          </div>
          <div class="overflow-y-auto px-5 py-4"><slot /></div>
          <div v-if="$slots.footer" class="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-3">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
