<script setup>
import { ref, watch } from 'vue'
import { Download } from '@lucide/vue'
import BaseDialog from './ui/BaseDialog.vue'
import StatusChip from './ui/StatusChip.vue'
import LoadingBlock from './ui/LoadingBlock.vue'
import ErrorState from './ui/ErrorState.vue'
import { documentsApi } from '@/api'
import { formatDate } from '@/utils/format'
import { useToast } from '@/composables/toast'

const props = defineProps({ open: Boolean, docId: [String, Number] })
const emit = defineEmits(['update:open'])
const toast = useToast()
const doc = ref(null)
const loading = ref(false)
const error = ref(null)

async function load() {
  loading.value = true; error.value = null; doc.value = null
  try { doc.value = await documentsApi.get(props.docId) } catch (e) { error.value = e } finally { loading.value = false }
}
watch(() => [props.open, props.docId], ([o]) => { if (o && props.docId) load() }, { immediate: true })

async function openFile() {
  try {
    const blob = await documentsApi.file(doc.value.id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) { toast.error(e.message) }
}
const ACCESS = { student: 'Students', faculty: 'Faculty', admin: 'Admin' }
</script>

<template>
  <BaseDialog :open="open" :title="doc?.title || 'Document'" size="lg" @update:open="emit('update:open', $event)">
    <LoadingBlock v-if="loading" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <div v-else-if="doc" class="space-y-4 text-sm">
      <div class="flex flex-wrap items-center gap-2">
        <StatusChip :label="doc.type" tone="info" /><StatusChip kind="processing" :value="doc.processing" />
        <span class="text-muted">v{{ doc.version }} · {{ doc.fileName }} · {{ doc.sizeKb }} KB<span v-if="doc.pages"> · {{ doc.pages }} page(s)</span></span>
        <button class="btn btn-secondary btn-sm ml-auto" @click="openFile"><Download class="size-4" /> Open file</button>
      </div>
      <p class="text-muted">Uploaded {{ formatDate(doc.uploadedAt) }} by {{ doc.uploadedBy }}<span v-if="doc.companyName"> · {{ doc.companyName }}</span><span v-if="doc.jobTitle"> — {{ doc.jobTitle }}</span></p>
      <p class="text-muted">Visible to: {{ doc.ownerStudentId ? 'The student and the placement cell' : doc.access.map((a) => ACCESS[a]).join(', ') }}</p>
      <p v-if="doc.processing === 'failed'" class="alert alert-warning">No text could be extracted (the file may be scanned images). The file is still stored.</p>
      <div v-if="doc.extractedExcerpts?.length">
        <p class="mb-2 font-medium">Extracted text</p>
        <div class="max-h-80 space-y-3 overflow-y-auto rounded-xl bg-slate-50 p-3">
          <div v-for="e in doc.extractedExcerpts" :key="e.page">
            <StatusChip tone="neutral" :label="`Page ${e.page}`" />
            <p class="mt-1 text-xs whitespace-pre-line text-slate-700">{{ e.text }}</p>
          </div>
        </div>
      </div>
    </div>
  </BaseDialog>
</template>
