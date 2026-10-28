<script setup>
// Search box that updates v-model 300 ms after the user stops typing.
import { ref, watch } from 'vue'
import { Search } from '@lucide/vue'
const props = defineProps({ modelValue: String, placeholder: { type: String, default: 'Search' } })
const emit = defineEmits(['update:modelValue'])
const local = ref(props.modelValue || '')
let timer
watch(local, (v) => { clearTimeout(timer); timer = setTimeout(() => emit('update:modelValue', v), 300) })
watch(() => props.modelValue, (v) => { if (v !== local.value) local.value = v || '' })
</script>

<template>
  <div class="relative min-w-48 flex-1 sm:max-w-xs">
    <Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
    <input v-model="local" type="search" class="input pl-9" :placeholder="placeholder" :aria-label="placeholder" />
  </div>
</template>
