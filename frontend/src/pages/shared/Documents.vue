<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Eye, FileText, RefreshCw, Replace, Trash2, Upload } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import Tabs from '@/components/ui/Tabs.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import UploadDialog from '@/components/UploadDialog.vue'
import DocumentPreviewDialog from '@/components/DocumentPreviewDialog.vue'
import { documentsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/toast'
import { formatDate } from '@/utils/format'

const auth = useAuthStore()
const toast = useToast()
const isStudent = computed(() => auth.role === 'student')
const canUpload = computed(() => isStudent.value || auth.can('documents.upload'))
const title = computed(() => (auth.role === 'faculty' ? 'Documents & Circulars' : 'Documents'))
const typeTabs = computed(() => [
  { value: '', label: 'All' },
  ...(isStudent.value ? [{ value: 'resume', label: 'Resume' }, { value: 'certificate', label: 'Certificate' }] : []),
  { value: 'brochure', label: 'Brochure' }, { value: 'circular', label: 'Circular' }, { value: 'eligibility', label: 'Eligibility' },
])

const f = reactive({ type: '', q: '', page: 1 })
watch(() => [f.type, f.q], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => documentsApi.list({ ...f, pageSize: 10 }), { watch: f })
const columns = [
  { key: 'title', label: 'Document' }, { key: 'type', label: 'Type', hide: 'sm' }, { key: 'uploaded', label: 'Uploaded', hide: 'md' },
  { key: 'access', label: 'Access', hide: 'lg' }, { key: 'status', label: 'Status' }, { key: 'actions', label: '', align: 'right' },
]
const ACCESS = { student: 'Students', faculty: 'Faculty', admin: 'Admin' }

const uploadOpen = ref(false)
const replacing = ref(null)
const previewId = ref(null)
const previewOpen = ref(false)
const deleting = ref(null)
const deleteOpen = ref(false)

function openUpload(doc = null) { replacing.value = doc; uploadOpen.value = true }
function preview(doc) { previewId.value = doc.id; previewOpen.value = true }
async function reprocess(doc) {
  try {
    const d = await documentsApi.reprocess(doc.id)
    toast[d.processing === 'indexed' ? 'success' : 'warning'](d.processing === 'indexed' ? 'Text extracted' : 'Still no text could be extracted')
    reload()
  } catch (e) { toast.error(e.message) }
}
async function remove() {
  await documentsApi.remove(deleting.value.id)
  toast.success('Document deleted')
  reload()
}
</script>

<template>
  <PageHeader :title="title" subtitle="Circulars, brochures and eligibility documents from the placement cell. Their text is searchable by the AI assistant.">
    <template #actions><button v-if="canUpload" class="btn btn-primary" @click="openUpload()"><Upload class="size-4" /> Upload</button></template>
  </PageHeader>
  <Tabs v-model="f.type" :tabs="typeTabs" />
  <DataTable :columns="columns" :rows="data?.items || []" :loading="loading" :error="error" :total="data?.total" :page="f.page" :page-size="10"
    empty-title="No documents" empty-message="Uploaded documents appear here." @page="f.page = $event" @retry="reload">
    <template #toolbar><SearchInput v-model="f.q" placeholder="Search title or company" /></template>
    <template #cell-title="{ row }">
      <button class="flex items-center gap-2 text-left" @click="preview(row)">
        <FileText class="size-5 shrink-0 text-red-600" />
        <span class="min-w-0">
          <span class="block font-medium hover:underline">{{ row.title }}</span>
          <span class="block text-xs text-muted">{{ row.ownerStudentId ? 'Personal document' : [row.companyName, row.jobTitle].filter(Boolean).join(' · ') || 'General' }} · v{{ row.version }}</span>
        </span>
      </button>
    </template>
    <template #cell-type="{ row }"><span class="capitalize">{{ row.type }}</span></template>
    <template #cell-uploaded="{ row }">{{ formatDate(row.uploadedAt) }}<span class="block text-xs text-muted">by {{ row.uploadedBy }}</span></template>
    <template #cell-access="{ row }">
      <span v-if="row.ownerStudentId" class="text-xs text-muted">Only you & placement cell</span>
      <span v-else class="flex flex-wrap gap-1"><StatusChip v-for="a in row.access" :key="a" tone="neutral" :label="ACCESS[a]" /></span>
    </template>
    <template #cell-status="{ row }">
      <StatusChip kind="processing" :value="row.processing" :label="row.processing === 'indexed' ? 'Searchable' : undefined" />
    </template>
    <template #cell-actions="{ row }">
      <div class="flex justify-end">
        <button class="btn-icon" aria-label="Preview" @click="preview(row)"><Eye class="size-4" /></button>
        <button v-if="row.canManage" class="btn-icon" aria-label="Replace file" @click="openUpload(row)"><Replace class="size-4" /></button>
        <button v-if="row.canManage && !isStudent && row.processing === 'failed'" class="btn-icon" aria-label="Retry text extraction" @click="reprocess(row)"><RefreshCw class="size-4" /></button>
        <button v-if="row.canManage" class="btn-icon hover:text-red-700" aria-label="Delete" @click="deleting = row; deleteOpen = true"><Trash2 class="size-4" /></button>
      </div>
    </template>
  </DataTable>

  <UploadDialog v-model:open="uploadOpen" :replace-doc="replacing" :default-type="isStudent ? 'resume' : 'circular'"
    @uploaded="toast.success(replacing ? 'File replaced' : 'Document uploaded'); reload()" />
  <DocumentPreviewDialog v-model:open="previewOpen" :doc-id="previewId" />
  <ConfirmDialog v-model:open="deleteOpen" title="Delete document?" confirm-label="Delete" tone="danger" :action="remove">
    “{{ deleting?.title }}” and its extracted text will be removed. The deletion is recorded in the audit log.
  </ConfirmDialog>
</template>
