<script setup>
defineProps({ title: String, subtitle: String, padded: { type: Boolean, default: true } })
</script>

<template>
  <section class="card overflow-hidden">
    <div v-if="title || $slots.actions" class="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
      <div class="min-w-0">
        <h2 class="text-base">{{ title }}</h2>
        <p v-if="subtitle" class="text-xs text-muted">{{ subtitle }}</p>
      </div>
      <div class="flex shrink-0 items-center gap-2"><slot name="actions" /></div>
    </div>
    <div :class="padded ? 'p-5' : ''"><slot /></div>
  </section>
</template>
