<script setup>
// Minimal, safe markdown for assistant answers: **bold**, _italic_, "- " bullets and "> " quotes.
// The text is HTML-escaped first, so nothing the model writes can inject markup.
import { computed } from 'vue'
const props = defineProps({ text: { type: String, default: '' } })

const escape = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const inline = (s) => escape(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/(^|\W)_(.+?)_(?=\W|$)/g, '$1<em>$2</em>')

const html = computed(() => {
  const out = []
  let list = null
  for (const raw of props.text.split('\n')) {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    if (bullet) { (list ||= []).push(`<li>${inline(bullet[1])}</li>`); continue }
    if (list) { out.push(`<ul class="my-1 list-disc space-y-0.5 pl-5">${list.join('')}</ul>`); list = null }
    if (/^>\s?/.test(line)) out.push(`<blockquote class="border-l-2 border-slate-300 pl-3 text-slate-600">${inline(line.replace(/^>\s?/, ''))}</blockquote>`)
    else if (line.trim()) out.push(`<p>${inline(line)}</p>`)
  }
  if (list) out.push(`<ul class="my-1 list-disc space-y-0.5 pl-5">${list.join('')}</ul>`)
  return out.join('')
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html : the content is escaped above -->
  <div class="space-y-2 leading-relaxed" v-html="html" />
</template>
