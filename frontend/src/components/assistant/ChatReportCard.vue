<script setup>
// A server-built report: KPI tiles, sections with tables (CSV each) and charts, plus print / save as PDF.
import { ref } from 'vue'
import { Download, Printer } from '@lucide/vue'
import ChatChartCard from './ChatChartCard.vue'
import { downloadText, formatDateTime, slugify, toCsv } from '@/utils/format'

const props = defineProps({ report: { type: Object, required: true } })
const card = ref(null)
const csv = (s) => downloadText(`${slugify(props.report.title + '-' + s.heading)}.csv`, toCsv(s.table.columns, s.table.rows))
const isNumber = (v) => typeof v === 'number'

// Print only this report: copy it into a hidden iframe with the page's styles.
function print() {
  const frame = document.createElement('iframe')
  frame.style.cssText = 'position:fixed;width:0;height:0;border:0'
  document.body.appendChild(frame)
  const doc = frame.contentDocument
  const styles = [...document.querySelectorAll('style, link[rel=stylesheet]')].map((n) => n.outerHTML).join('')
  const clone = card.value.cloneNode(true)
  clone.querySelectorAll('[data-noprint]').forEach((n) => n.remove())
  clone.querySelectorAll('.overflow-auto').forEach((n) => { n.style.maxHeight = 'none'; n.style.overflow = 'visible' })
  // canvases don't clone their pixels; swap in images
  const src = card.value.querySelectorAll('canvas')
  clone.querySelectorAll('canvas').forEach((c, i) => { const img = new Image(); img.src = src[i].toDataURL(); img.style.maxWidth = '100%'; c.replaceWith(img) })
  doc.open()
  doc.write(`<!doctype html><html><head><title>${props.report.title}</title>${styles}</head><body style="padding:24px;background:#fff">${clone.outerHTML}</body></html>`)
  doc.close()
  setTimeout(() => { frame.contentWindow.print(); setTimeout(() => frame.remove(), 1000) }, 400)
}
</script>

<template>
  <div ref="card" class="rounded-xl border border-line bg-white p-4">
    <div class="mb-3 flex flex-wrap items-start gap-2">
      <div class="min-w-0 flex-1">
        <p class="font-semibold">{{ report.title }}</p>
        <p class="text-xs text-muted"><span v-if="report.subtitle">{{ report.subtitle }} · </span>Generated {{ formatDateTime(report.generatedAt) }}</p>
      </div>
      <button data-noprint class="btn btn-secondary btn-sm" @click="print"><Printer class="size-3.5" /> Print / PDF</button>
    </div>
    <div class="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div v-for="k in report.kpis" :key="k.label" class="rounded-lg bg-slate-50 p-2.5">
        <p class="text-[11px] text-muted">{{ k.label }}</p><p class="text-lg font-semibold">{{ k.value }}</p>
      </div>
    </div>
    <section v-for="s in report.sections" :key="s.heading" class="mb-4 last:mb-0">
      <div class="mb-1.5 flex items-center justify-between gap-2">
        <p class="text-sm font-semibold">{{ s.heading }}</p>
        <button v-if="s.table" data-noprint class="text-xs text-muted hover:text-ink" @click="csv(s)"><Download class="inline size-3" /> CSV</button>
      </div>
      <div v-if="s.table" class="max-h-90 overflow-auto rounded-lg border border-line">
        <p v-if="!s.table.rows.length" class="p-3 text-xs text-muted">No rows for these filters.</p>
        <table v-else class="table text-xs">
          <thead class="sticky top-0"><tr><th v-for="c in s.table.columns" :key="c">{{ c }}</th></tr></thead>
          <tbody><tr v-for="(r, i) in s.table.rows" :key="i"><td v-for="(v, j) in r" :key="j" :class="isNumber(v) && 'text-right'">{{ v }}</td></tr></tbody>
        </table>
      </div>
      <p v-if="s.note" class="mt-1 text-xs text-muted">{{ s.note }}</p>
      <ChatChartCard v-if="s.chart" class="mt-2" :chart="s.chart" />
    </section>
    <p v-if="report.truncated" class="mt-2 text-xs text-muted">Some tables were cut to 100 rows. Use the Reports and list pages for everything.</p>
  </div>
</template>
