<script setup>
// Free-text chips (skills, interests). Enter or comma adds; suggestions appear as a datalist.
import { ref } from 'vue'
import { X } from '@lucide/vue'
const props = defineProps({ modelValue: { type: Array, default: () => [] }, suggestions: { type: Array, default: () => [] }, placeholder: String, max: { type: Number, default: 30 }, disabled: Boolean, id: String })
const emit = defineEmits(['update:modelValue'])
const text = ref('')
const listId = `tags-${Math.random().toString(36).slice(2)}`

function add() {
  const v = text.value.trim().replace(/,$/, '')
  text.value = ''
  if (!v || props.modelValue.length >= props.max) return
  if (props.modelValue.some((t) => t.toLowerCase() === v.toLowerCase())) return
  emit('update:modelValue', [...props.modelValue, v.slice(0, 40)])
}
const remove = (i) => emit('update:modelValue', props.modelValue.filter((_, j) => j !== i))
function onKey(e) {
  if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add() }
  else if (e.key === 'Backspace' && !text.value && props.modelValue.length) remove(props.modelValue.length - 1)
}
</script>

<template>
  <div class="input flex min-h-10 flex-wrap items-center gap-1.5 py-1.5" :class="disabled && 'bg-slate-50'">
    <span v-for="(t, i) in modelValue" :key="t" class="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
      {{ t }}
      <button v-if="!disabled" type="button" class="hover:text-red-700" :aria-label="`Remove ${t}`" @click="remove(i)"><X class="size-3" /></button>
    </span>
    <input v-if="!disabled" :id="id" v-model="text" :list="listId" class="min-w-32 flex-1 border-0 p-0.5 text-sm outline-none focus:ring-0"
      :placeholder="modelValue.length ? '' : placeholder" @keydown="onKey" @blur="add" />
    <datalist :id="listId"><option v-for="s in suggestions" :key="s" :value="s" /></datalist>
  </div>
</template>
