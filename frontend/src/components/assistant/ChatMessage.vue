<script setup>
import { onMounted, ref } from 'vue'
import { Bot, FileText } from '@lucide/vue'
import Avatar from '../ui/Avatar.vue'
import BaseDialog from '../ui/BaseDialog.vue'
import JobCard from '../JobCard.vue'
import DocumentPreviewDialog from '../DocumentPreviewDialog.vue'
import MarkdownText from './MarkdownText.vue'
import ChatChartCard from './ChatChartCard.vue'
import ChatReportCard from './ChatReportCard.vue'
import ActionCard from './ActionCard.vue'
import { jobsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { formatTime } from '@/utils/format'

const props = defineProps({ message: { type: Object, required: true } })
const emit = defineEmits(['changed'])
const auth = useAuthStore()
const base = useBase()
const jobs = ref([])
const source = ref(null)
const sourceOpen = ref(false)
const docOpen = ref(false)

onMounted(async () => {
  const ids = props.message.jobIds || []
  const views = await Promise.all(ids.map((id) => jobsApi.get(id).catch(() => null)))
  jobs.value = views.filter(Boolean)
})
function openSource(s) { source.value = s; if (s.snippet) sourceOpen.value = true; else docOpen.value = true }
const isUser = props.message.role === 'user'
</script>

<template>
  <div class="flex gap-3" :class="isUser && 'flex-row-reverse'">
    <Avatar v-if="isUser" :name="auth.user?.name" size="sm" />
    <span v-else class="flex size-7 shrink-0 items-center justify-center rounded-lg bg-navy-800 text-white"><Bot class="size-4" /></span>
    <div class="min-w-0 max-w-[min(48rem,100%)] space-y-2" :class="isUser && 'flex flex-col items-end'">
      <div class="rounded-2xl px-4 py-2.5 text-sm" :class="isUser ? 'bg-brand-600 text-white' : 'border border-line bg-white'">
        <p v-if="isUser" class="whitespace-pre-wrap">{{ message.text }}</p>
        <MarkdownText v-else :text="message.text" />
      </div>
      <ChatReportCard v-for="(r, i) in message.reports || []" :key="'r' + i" :report="r" />
      <ChatChartCard v-for="(c, i) in message.charts || []" :key="'c' + i" :chart="c" />
      <div v-if="jobs.length" class="grid gap-2 sm:grid-cols-2">
        <JobCard v-for="v in jobs" :key="v.job.id" :view="v" compact :detail-to="`${base}/jobs/${v.job.id}`" />
      </div>
      <ActionCard v-if="message.action" :action="message.action" @changed="emit('changed')" />
      <div v-if="message.sources?.length || message.tools?.length" class="flex flex-wrap items-center gap-1.5">
        <button v-for="s in message.sources || []" :key="s.documentId + s.page" class="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5 text-xs hover:bg-slate-50"
          @click="openSource(s)"><FileText class="size-3" /> {{ s.title }} · p.{{ s.page }}</button>
        <span v-for="(t, i) in message.tools || []" :key="'t' + i" class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600"
          :class="t.status === 'denied' && 'bg-red-50 text-red-700'">{{ t.tool }}<span v-if="t.status === 'denied'"> · denied</span></span>
      </div>
      <p class="text-[11px] text-slate-400">{{ formatTime(message.at) }}</p>
    </div>
    <BaseDialog v-model:open="sourceOpen" :title="source ? `${source.title} · page ${source.page}` : ''">
      <p class="rounded-lg bg-slate-50 p-3 text-sm whitespace-pre-line">{{ source?.snippet }}</p>
      <template #footer><button class="btn btn-secondary" @click="sourceOpen = false; docOpen = true">Open document</button></template>
    </BaseDialog>
    <DocumentPreviewDialog v-model:open="docOpen" :doc-id="source?.documentId" />
  </div>
</template>
