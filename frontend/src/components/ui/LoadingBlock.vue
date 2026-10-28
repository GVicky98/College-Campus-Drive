<script setup>
defineProps({ rows: { type: Number, default: 4 } })
</script>

<template>
  <div class="space-y-3 p-5" aria-busy="true" aria-label="Loading">
    <div class="skeleton h-5 w-1/3" />
    <div v-for="i in rows" :key="i" class="skeleton h-4" :style="{ width: `${90 - i * 7}%` }" />
  </div>
</template>
