<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: String,
  crumbs: { type: Array, default: () => [] }, // [{ label, to? }]
})
</script>

<template>
  <header class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div class="min-w-0">
      <nav v-if="crumbs.length" class="mb-1 flex flex-wrap items-center gap-1 text-xs text-muted" aria-label="Breadcrumb">
        <template v-for="(c, i) in crumbs" :key="i">
          <RouterLink v-if="c.to" :to="c.to" class="hover:text-ink hover:underline">{{ c.label }}</RouterLink>
          <span v-else class="text-ink">{{ c.label }}</span>
          <span v-if="i < crumbs.length - 1">/</span>
        </template>
      </nav>
      <h1 class="text-2xl text-ink">{{ title }}</h1>
      <div v-if="subtitle || $slots.subtitle" class="mt-1 text-sm text-muted">
        <slot name="subtitle">{{ subtitle }}</slot>
      </div>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
