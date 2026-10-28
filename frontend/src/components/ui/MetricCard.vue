<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: String,
  icon: [Object, Function],
  tone: { type: String, default: 'blue' }, // blue | green | amber | red | purple | slate
  to: [String, Object],
})
const tones = {
  blue: 'bg-blue-50 text-blue-700',
  green: 'bg-green-50 text-green-700',
  amber: 'bg-amber-50 text-amber-700',
  red: 'bg-red-50 text-red-700',
  purple: 'bg-violet-50 text-violet-700',
  slate: 'bg-slate-100 text-slate-700',
}
</script>

<template>
  <component :is="to ? 'RouterLink' : 'div'" :to="to"
    class="card flex items-start gap-3 p-4 transition" :class="to && 'hover:border-brand-500 hover:shadow-sm'">
    <div v-if="icon" class="flex size-10 shrink-0 items-center justify-center rounded-xl" :class="tones[tone]">
      <component :is="icon" class="size-5" />
    </div>
    <div class="min-w-0">
      <p class="text-xs font-medium text-muted">{{ label }}</p>
      <p class="mt-0.5 text-2xl font-semibold text-ink">{{ value }}</p>
      <p v-if="hint" class="mt-0.5 text-xs text-muted">{{ hint }}</p>
    </div>
  </component>
</template>
