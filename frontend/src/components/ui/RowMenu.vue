<script setup>
// A "⋮" menu for table rows. The panel is teleported to <body> so table scrolling can't clip it.
import { nextTick, ref } from 'vue'
import { MoreVertical } from '@lucide/vue'
defineProps({ label: { type: String, default: 'Actions' } })
const open = ref(false)
const pos = ref({ top: 0, left: 0 })
const btn = ref(null)

async function toggle() {
  open.value = !open.value
  if (!open.value) return
  await nextTick()
  const r = btn.value.getBoundingClientRect()
  pos.value = { top: r.bottom + 4, left: Math.max(8, r.right - 208) }
}
const close = () => { open.value = false }
</script>

<template>
  <span class="inline-block" @click.stop>
    <button ref="btn" class="btn-icon" :aria-label="label" aria-haspopup="menu" :aria-expanded="open" @click="toggle"><MoreVertical class="size-4" /></button>
    <Teleport to="body">
      <div v-if="open" class="fixed inset-0 z-40" @click="close" @scroll="close" />
      <div v-if="open" role="menu" class="card fixed z-50 w-52 p-1 text-left text-sm shadow-lg" :style="{ top: pos.top + 'px', left: pos.left + 'px' }" @click="close">
        <slot />
      </div>
    </Teleport>
  </span>
</template>
