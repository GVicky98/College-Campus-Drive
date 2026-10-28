<script setup>
import Avatar from './ui/Avatar.vue'
defineProps({ company: Object, size: { type: String, default: 'md' } })
</script>

<template>
  <Avatar :name="company?.name || '?'" :color="company?.color" :size="size" />
</template>
