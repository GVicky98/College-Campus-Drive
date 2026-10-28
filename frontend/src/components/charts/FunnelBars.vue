<script setup>
// A simple funnel: one horizontal bar per stage, as a share of the first stage.
import { computed } from 'vue'
const props = defineProps({ stages: { type: Array, default: () => [] } }) // [{ stage, value }]
const max = computed(() => Math.max(1, ...props.stages.map((s) => s.value)))
</script>

<template>
  <ul class="space-y-3">
    <li v-for="(s, i) in stages" :key="s.stage">
      <div class="mb-1 flex justify-between text-sm"><span>{{ s.stage }}</span><span class="font-semibold">{{ s.value }}</span></div>
      <div class="h-3 rounded-full bg-slate-100">
        <div class="h-3 rounded-full transition-all" :style="{ width: `${(100 * s.value) / max}%`, opacity: 1 - i * 0.1 }" style="background: #2563eb" />
      </div>
    </li>
  </ul>
</template>
