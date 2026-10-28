<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'
const props = defineProps({ page: Number, pageSize: Number, total: Number })
const emit = defineEmits(['change'])
const pages = computed(() => Math.max(1, Math.ceil((props.total || 0) / (props.pageSize || 1))))
const from = computed(() => (props.total ? (props.page - 1) * props.pageSize + 1 : 0))
const to = computed(() => Math.min(props.total, props.page * props.pageSize))
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-xs text-muted">
    <span>Showing {{ from }}–{{ to }} of {{ total }}</span>
    <div class="flex items-center gap-1">
      <button class="btn-icon" :disabled="page <= 1" aria-label="Previous page" @click="emit('change', page - 1)"><ChevronLeft class="size-4" /></button>
      <span class="px-2">Page {{ page }} of {{ pages }}</span>
      <button class="btn-icon" :disabled="page >= pages" aria-label="Next page" @click="emit('change', page + 1)"><ChevronRight class="size-4" /></button>
    </div>
  </div>
</template>
