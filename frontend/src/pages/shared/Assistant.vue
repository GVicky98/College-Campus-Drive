<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Bot, History, Plus, Send, Trash2 } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ChatMessage from '@/components/assistant/ChatMessage.vue'
import { assistantApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/format'

const auth = useAuthStore()
const MAX = 2000
const status = ref(null)
const suggestions = ref([])
const list = ref([])
const listLoading = ref(true)
const listError = ref('')
const current = ref(null) // { id, title, messages }
const input = ref('')
const sending = ref(false)
const pending = ref('') // the question being answered (shown at once)
const sendError = ref(null) // { title, message, text }
const historyOpen = ref(false)
const deleting = ref(null)
const deleteOpen = ref(false)
const scroller = ref(null)

const available = computed(() => status.value?.available !== false)
const messages = computed(() => current.value?.messages || [])
const WELCOME = {
  student: 'Ask about jobs you are eligible for, your applications, interviews and offers, or the latest circulars. I can also prepare applications and reminders for you to confirm.',
  faculty: 'Ask about students, applicants, drives, interviews and offers, or ask for a chart or report. I can prepare stage changes, companies and more for you to confirm.',
  admin: 'Ask about accounts, policies, placement statistics or the audit log, or ask for a chart or report. I can prepare account, company and policy changes for you to confirm.',
}

async function loadList() {
  listLoading.value = true
  listError.value = ''
  try { list.value = await assistantApi.conversations() } catch (e) { listError.value = e.message } finally { listLoading.value = false }
}
async function open(id) {
  historyOpen.value = false
  sendError.value = null
  current.value = await assistantApi.conversation(id)
  scrollDown()
}
function startNew() { current.value = null; sendError.value = null; historyOpen.value = false }
async function scrollDown() { await nextTick(); scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' }) }

onMounted(async () => {
  const [s, sug] = await Promise.all([assistantApi.status().catch(() => null), assistantApi.suggestions().catch(() => [])])
  status.value = s
  suggestions.value = sug
  await loadList()
  if (list.value.length) open(list.value[0].id)
})

async function send(text = input.value) {
  text = text.trim()
  if (!text || sending.value || !available.value) return
  if (text.length > MAX) { sendError.value = { title: 'Message too long', message: `Keep it under ${MAX} characters.`, text }; return }
  sending.value = true
  pending.value = text
  input.value = ''
  sendError.value = null
  scrollDown()
  try {
    current.value = await assistantApi.chat(text, current.value?.id ? Number(current.value.id) : undefined)
    loadList()
  } catch (e) {
    const titles = { 503: 'The assistant is unavailable', 429: 'Slow down a little', 504: 'That took too long' }
    sendError.value = { title: titles[e.status] || 'Message not sent', message: e.message, text }
    if (e.status === 503) status.value = { available: false, reason: e.message }
  } finally {
    sending.value = false
    pending.value = ''
    scrollDown()
  }
}
function retry() { const t = sendError.value.text; sendError.value = null; send(t) }
function onKey(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send() }
}
async function refreshCurrent() { if (current.value?.id) current.value = await assistantApi.conversation(current.value.id) }
async function remove() {
  await assistantApi.remove(deleting.value.id)
  if (current.value?.id === deleting.value.id) current.value = null
  loadList()
}
</script>

<template>
  <PageHeader title="AI assistant" subtitle="Answers come from your live placement records, within your permissions.">
    <template #actions>
      <button class="btn btn-secondary lg:hidden" @click="historyOpen = true"><History class="size-4" /> History</button>
      <button class="btn btn-primary" @click="startNew"><Plus class="size-4" /> New conversation</button>
    </template>
  </PageHeader>

  <div class="card flex h-[calc(100vh-13rem)] min-h-[32rem] overflow-hidden">
    <!-- history -->
    <div v-if="historyOpen" class="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" @click="historyOpen = false" />
    <aside class="fixed inset-y-0 left-0 z-40 w-72 flex-col border-r border-line bg-white lg:static lg:z-auto lg:flex lg:w-64"
      :class="historyOpen ? 'flex' : 'hidden'">
      <div class="border-b border-line p-3"><button class="btn btn-secondary w-full" @click="startNew"><Plus class="size-4" /> New conversation</button></div>
      <div class="flex-1 overflow-y-auto p-2">
        <p v-if="listLoading" class="p-3 text-sm text-muted">Loading…</p>
        <div v-else-if="listError" class="p-3 text-sm text-red-700">{{ listError }} <button class="link" @click="loadList">Retry</button></div>
        <p v-else-if="!list.length" class="p-3 text-sm text-muted">No conversations yet.</p>
        <ul v-else class="space-y-0.5">
          <li v-for="c in list" :key="c.id" class="group flex items-center rounded-lg" :class="current?.id === c.id ? 'bg-brand-50' : 'hover:bg-slate-50'">
            <button class="min-w-0 flex-1 px-3 py-2 text-left" @click="open(c.id)">
              <span class="block truncate text-sm" :class="current?.id === c.id && 'font-medium text-brand-700'">{{ c.title }}</span>
              <span class="text-[11px] text-muted">{{ timeAgo(c.updatedAt) }}</span>
            </button>
            <button class="btn-icon mr-1 opacity-60 group-hover:opacity-100 hover:text-red-700" :aria-label="`Delete ${c.title}`" @click="deleting = c; deleteOpen = true"><Trash2 class="size-3.5" /></button>
          </li>
        </ul>
      </div>
    </aside>

    <!-- chat -->
    <section class="flex min-w-0 flex-1 flex-col">
      <p v-if="status && !status.available" class="alert alert-warning m-4 mb-0">
        <b>AI assistant not configured.</b> {{ status.reason }}
      </p>
      <div ref="scroller" class="flex-1 space-y-5 overflow-y-auto bg-page/50 p-4 sm:p-6" aria-live="polite">
        <div v-if="!messages.length && !pending" class="mx-auto flex max-w-xl flex-col items-center pt-8 text-center">
          <span class="mb-3 flex size-12 items-center justify-center rounded-2xl bg-navy-800 text-white"><Bot class="size-6" /></span>
          <p class="text-lg font-semibold">How can I help?</p>
          <p class="mt-1 text-sm text-muted">{{ WELCOME[auth.role] }}</p>
          <div class="mt-6 flex flex-wrap justify-center gap-2">
            <button v-for="s in suggestions" :key="s" class="rounded-full border border-line bg-white px-3 py-1.5 text-sm hover:border-brand-500 hover:text-brand-700 disabled:opacity-50"
              :disabled="!available || sending" @click="send(s)">{{ s }}</button>
          </div>
        </div>
        <ChatMessage v-for="m in messages" :key="m.id" :message="m" @changed="refreshCurrent" />
        <template v-if="pending">
          <ChatMessage :message="{ id: 'pending', role: 'user', text: pending, at: new Date().toISOString() }" />
          <div class="flex items-center gap-3">
            <span class="flex size-7 items-center justify-center rounded-lg bg-navy-800 text-white"><Bot class="size-4" /></span>
            <span class="flex gap-1 rounded-2xl border border-line bg-white px-4 py-3" aria-label="The assistant is thinking">
              <span v-for="i in 3" :key="i" class="size-1.5 animate-bounce rounded-full bg-slate-400" :style="{ animationDelay: `${i * 0.15}s` }" />
            </span>
          </div>
        </template>
        <div v-if="sendError" class="alert alert-error items-start">
          <div class="flex-1"><p class="font-medium">{{ sendError.title }}</p><p>{{ sendError.message }}</p><p class="mt-1 text-xs opacity-80">“{{ sendError.text.slice(0, 160) }}”</p></div>
          <button class="btn btn-secondary btn-sm" @click="retry">Retry</button>
        </div>
      </div>
      <div class="border-t border-line bg-white p-3">
        <div v-if="messages.length && suggestions.length" class="mb-2 flex gap-2 overflow-x-auto pb-1 sm:hidden">
          <button v-for="s in suggestions.slice(0, 4)" :key="s" class="shrink-0 rounded-full border border-line px-3 py-1 text-xs" :disabled="!available || sending" @click="send(s)">{{ s }}</button>
        </div>
        <form class="flex items-end gap-2" @submit.prevent="send()">
          <div class="relative flex-1">
            <textarea v-model="input" rows="1" class="input max-h-32 min-h-10 resize-none py-2.5 pr-14" :placeholder="available ? 'Ask a question… (Shift+Enter for a new line)' : 'The assistant is not configured'"
              :disabled="!available" aria-label="Message" @keydown="onKey"
              @input="(e) => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px' }" />
            <span v-if="input.length > MAX * 0.8" class="absolute right-3 bottom-2 text-[11px]" :class="input.length > MAX ? 'text-red-700' : 'text-muted'">{{ input.length }}/{{ MAX }}</span>
          </div>
          <button type="submit" class="btn btn-primary h-10 w-10 p-0" :disabled="!input.trim() || sending || !available" aria-label="Send"><Send class="size-4" /></button>
        </form>
      </div>
    </section>
  </div>

  <ConfirmDialog v-model:open="deleteOpen" title="Delete conversation?" confirm-label="Delete" tone="danger" :action="remove">
    “{{ deleting?.title }}” is removed from your history. Any changes it prepared that you have not confirmed are cancelled.
  </ConfirmDialog>
</template>
