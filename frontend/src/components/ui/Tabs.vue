<script setup>
// v-model holds the active tab value. tabs: [{ value, label, count? }]
defineProps({ modelValue: [String, Number], tabs: { type: Array, required: true } })
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="mb-4 flex gap-1 overflow-x-auto border-b border-line" role="tablist">
    <button v-for="t in tabs" :key="t.value" role="tab" :aria-selected="modelValue === t.value"
      class="tab" :class="modelValue === t.value && 'tab-active'" @click="$emit('update:modelValue', t.value)">
      {{ t.label }}<span v-if="t.count !== undefined" class="ml-1.5 rounded-full bg-slate-100 px-1.5 text-xs text-slate-600">{{ t.count }}</span>
    </button>
  </div>
</template>
