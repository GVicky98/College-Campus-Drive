<script setup>
// Small labelled select for filter bars. options: [{ value, label }] or strings.
import { computed } from 'vue'
const props = defineProps({ modelValue: [String, Number], options: { type: Array, default: () => [] }, label: String, allLabel: { type: String, default: 'All' } })
defineEmits(['update:modelValue'])
const opts = computed(() => props.options.map((o) => (typeof o === 'object' ? o : { value: o, label: o })))
</script>

<template>
  <label class="flex items-center gap-2 text-xs text-muted">
    <span v-if="label" class="whitespace-nowrap">{{ label }}</span>
    <select class="input w-auto py-1.5 pr-8" :value="modelValue ?? ''" @change="$emit('update:modelValue', $event.target.value)">
      <option value="">{{ allLabel }}</option>
      <option v-for="o in opts" :key="o.value" :value="String(o.value)">{{ o.label }}</option>
    </select>
  </label>
</template>
