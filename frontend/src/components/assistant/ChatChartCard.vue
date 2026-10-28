<script setup>
// A server-computed chart with a style switcher, a table view and CSV export.
import { ref } from 'vue'
import { Download } from '@lucide/vue'
import ChartCanvas from '../charts/ChartCanvas.vue'
import { downloadText, slugify, toCsv } from '@/utils/format'

const props = defineProps({ chart: { type: Object, required: true }, embedded: Boolean })
const view = ref(props.chart.type)
const NAMES = { pie: 'Pie', donut: 'Donut', bar: 'Bar', hbar: 'Horizontal', stacked: 'Stacked', line: 'Line', area: 'Area', table: 'Table' }

function csv() {
  const rows = props.chart.labels.map((l, i) => [l, ...props.chart.series.map((s) => s.values[i])])
  downloadText(`${slugify(props.chart.title)}.csv`, toCsv(['', ...props.chart.series.map((s) => s.name)], rows))
}
</script>

<template>
  <div class="rounded-xl border border-line bg-white p-3" :class="embedded && 'border-0 p-0'">
    <div class="mb-2 flex flex-wrap items-start gap-2">
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold">{{ chart.title }}</p>
        <p v-if="chart.subtitle" class="text-xs text-muted">{{ chart.subtitle }}</p>
      </div>
      <div class="flex flex-wrap gap-1" data-noprint role="group" aria-label="Chart style">
        <button v-for="t in [...chart.types, 'table']" :key="t" class="rounded-md border px-2 py-0.5 text-xs"
          :class="view === t ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-line text-muted hover:bg-slate-50'" @click="view = t">{{ NAMES[t] }}</button>
        <button class="rounded-md border border-line px-2 py-0.5 text-xs text-muted hover:bg-slate-50" @click="csv"><Download class="inline size-3" /> CSV</button>
      </div>
    </div>
    <div v-if="view === 'table'" class="max-h-72 overflow-auto rounded-lg border border-line">
      <table class="table text-xs">
        <thead><tr><th></th><th v-for="s in chart.series" :key="s.name" class="text-right">{{ s.name }}</th></tr></thead>
        <tbody><tr v-for="(l, i) in chart.labels" :key="l"><td>{{ l }}</td>
          <td v-for="s in chart.series" :key="s.name" class="text-right">{{ s.values[i] }}{{ chart.unit || '' }}</td></tr></tbody>
      </table>
    </div>
    <ChartCanvas v-else :type="view" :labels="chart.labels" :series="chart.series" :unit="chart.unit || ''" :height="240" />
  </div>
</template>
