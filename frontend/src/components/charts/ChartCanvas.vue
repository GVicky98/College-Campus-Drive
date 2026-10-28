<script setup>
// One Chart.js wrapper for every chart in the app.
//   type: 'bar' | 'hbar' | 'stacked' | 'line' | 'area' | 'pie' | 'donut'
//   labels: string[], series: [{ name, values: number[] }], unit?: string
import { computed } from 'vue'
import { Bar, Doughnut, Line, Pie } from 'vue-chartjs'
import {
  ArcElement, BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip,
} from 'chart.js'

ChartJS.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip)
ChartJS.defaults.font.family = 'Inter, ui-sans-serif, system-ui, sans-serif'
ChartJS.defaults.color = '#5b6b86'

const props = defineProps({
  type: { type: String, default: 'bar' },
  labels: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  height: { type: Number, default: 280 },
})

const PALETTE = ['#2563eb', '#0f766e', '#d97706', '#7c3aed', '#db2777', '#475569', '#0891b2', '#65a30d']

const isPie = computed(() => props.type === 'pie' || props.type === 'donut')
const component = computed(() => (isPie.value ? (props.type === 'pie' ? Pie : Doughnut) : props.type === 'line' || props.type === 'area' ? Line : Bar))
const empty = computed(() => !props.labels.length || props.series.every((s) => s.values.every((v) => !v)))

const data = computed(() => ({
  labels: props.labels,
  datasets: props.series.map((s, i) => {
    const color = PALETTE[i % PALETTE.length]
    if (isPie.value) return { label: s.name, data: s.values, backgroundColor: props.labels.map((_, j) => PALETTE[j % PALETTE.length]), borderWidth: 2, borderColor: '#fff' }
    if (props.type === 'line' || props.type === 'area')
      return { label: s.name, data: s.values, borderColor: color, backgroundColor: color + '33', fill: props.type === 'area', cubicInterpolationMode: 'monotone', pointRadius: 3 }
    return { label: s.name, data: s.values, backgroundColor: color, borderRadius: 4, maxBarThickness: 36 }
  }),
}))

const options = computed(() => {
  const fmt = (v) => `${Number(v).toLocaleString('en-IN')}${props.unit}`
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: isPie.value || props.series.length > 1, position: 'bottom', labels: { boxWidth: 12, boxHeight: 12 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label || ctx.label}: ${fmt(ctx.parsed?.y ?? ctx.parsed?.x ?? ctx.parsed)}` } },
    },
  }
  if (isPie.value) return { ...base, cutout: props.type === 'donut' ? '60%' : 0 }
  const horizontal = props.type === 'hbar'
  const stacked = props.type === 'stacked'
  const valueAxis = { beginAtZero: true, stacked, grid: { color: '#eef2f7' }, ticks: { precision: 0, callback: (v) => fmt(v) } }
  const labelAxis = { stacked, grid: { display: false } }
  return { ...base, indexAxis: horizontal ? 'y' : 'x', scales: horizontal ? { x: valueAxis, y: labelAxis } : { x: labelAxis, y: valueAxis } }
})
</script>

<template>
  <div :style="{ height: height + 'px' }" class="relative">
    <p v-if="empty" class="flex h-full items-center justify-center text-sm text-muted">No data for these filters</p>
    <component :is="component" v-else :data="data" :options="options" />
  </div>
</template>
