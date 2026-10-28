<script setup>
import { computed } from 'vue'
import { initials } from '@/utils/format'
const props = defineProps({ name: { type: String, default: '' }, color: String, size: { type: String, default: 'md' } })
const text = computed(() => initials(props.name) || '?')
const sizes = { sm: 'size-7 text-[11px]', md: 'size-9 text-xs', lg: 'size-12 text-sm' }
</script>

<template>
  <span class="inline-flex shrink-0 items-center justify-center rounded-lg font-semibold text-white"
    :class="sizes[size]" :style="{ backgroundColor: color || '#1e3a7b' }" aria-hidden="true">{{ text }}</span>
</template>
