<script setup>
// Shows a skeleton while loading, an error card on failure, otherwise the default slot.
import LoadingBlock from './LoadingBlock.vue'
import ErrorState from './ErrorState.vue'
defineProps({ loading: Boolean, error: Object, hasData: { type: Boolean, default: true }, rows: { type: Number, default: 4 } })
defineEmits(['retry'])
</script>

<template>
  <ErrorState v-if="error && !hasData" :error="error" @retry="$emit('retry')" />
  <LoadingBlock v-else-if="loading && !hasData" :rows="rows" />
  <slot v-else-if="hasData" />
</template>
