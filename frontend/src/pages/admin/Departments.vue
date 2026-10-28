<script setup>
import { computed, ref } from 'vue'
import { Pencil, Plus, Trash2 } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import Forbidden from '@/pages/auth/Forbidden.vue'
import AcademicDialog from './parts/AcademicDialog.vue'
import { adminApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useReference } from '@/composables/useReference'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/toast'

const auth = useAuthStore()
const toast = useToast()
const reference = useReference()
const { data, loading, error, reload } = useAsync(() => adminApi.academic())
const tab = ref('departments')
const addLabel = computed(() => ({ departments: 'Add department', courses: 'Add programme', years: 'Add academic year' })[tab.value])
const deptCode = (id) => data.value?.departments.find((d) => d.id === id)?.code || '—'

const dialog = ref({ open: false, kind: 'department', item: null })
const KIND = { departments: 'department', courses: 'course', years: 'year' }
function openDialog(item = null) { dialog.value = { open: true, kind: KIND[tab.value], item } }
async function saved() { toast.success('Saved'); await reload(); reference.reload() }

const confirm = ref({ open: false })
function remove(kind, item) {
  confirm.value = { open: true, title: `Delete ${item.code}?`, text: kind === 'department'
    ? 'A department that still has students, programmes, staff, jobs or policies cannot be deleted.' : 'This programme is removed.',
    run: async () => { await (kind === 'department' ? adminApi.deleteDepartment(item.id) : adminApi.deleteCourse(item.id)); toast.success('Deleted'); reload(); reference.reload() } }
}
const deptCols = [{ key: 'code', label: 'Code' }, { key: 'name', label: 'Department' }, { key: 'headName', label: 'Head', hide: 'md' },
  { key: 'students', label: 'Students', align: 'right' }, { key: 'courses', label: 'Programmes', align: 'right', hide: 'sm' }, { key: 'actions', label: '', align: 'right' }]
const courseCols = [{ key: 'code', label: 'Code' }, { key: 'name', label: 'Programme' }, { key: 'degree', label: 'Degree' },
  { key: 'dept', label: 'Department', hide: 'sm' }, { key: 'durationYears', label: 'Years', align: 'right', hide: 'sm' }, { key: 'actions', label: '', align: 'right' }]
const yearCols = [{ key: 'label', label: 'Academic year' }, { key: 'graduationYear', label: 'Graduation batch' }, { key: 'active', label: 'Status' }, { key: 'actions', label: '', align: 'right' }]
</script>

<template>
  <Forbidden v-if="auth.role !== 'admin'" embedded />
  <template v-else>
    <PageHeader title="Departments & courses" subtitle="Academic structure used by profiles, eligibility rules and policies.">
      <template #actions><button class="btn btn-primary" @click="openDialog()"><Plus class="size-4" /> {{ addLabel }}</button></template>
    </PageHeader>
    <Tabs v-model="tab" :tabs="[{ value: 'departments', label: 'Departments' }, { value: 'courses', label: 'Degree programmes' }, { value: 'years', label: 'Academic years & batches' }]" />
    <DataTable v-if="tab === 'departments'" :columns="deptCols" :rows="data?.departments || []" :loading="loading" :error="error" @retry="reload">
      <template #cell-code="{ row }"><span class="font-mono text-xs">{{ row.code }}</span></template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end"><button class="btn-icon" aria-label="Edit" @click="openDialog(row)"><Pencil class="size-4" /></button>
          <button class="btn-icon hover:text-red-700" aria-label="Delete" @click="remove('department', row)"><Trash2 class="size-4" /></button></div>
      </template>
    </DataTable>
    <DataTable v-else-if="tab === 'courses'" :columns="courseCols" :rows="data?.courses || []" :loading="loading" :error="error" @retry="reload">
      <template #cell-code="{ row }"><span class="font-mono text-xs">{{ row.code }}</span></template>
      <template #cell-dept="{ row }">{{ deptCode(row.departmentId) }}</template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end"><button class="btn-icon" aria-label="Edit" @click="openDialog(row)"><Pencil class="size-4" /></button>
          <button class="btn-icon hover:text-red-700" aria-label="Delete" @click="remove('course', row)"><Trash2 class="size-4" /></button></div>
      </template>
    </DataTable>
    <DataTable v-else :columns="yearCols" :rows="data?.academicYears || []" :loading="loading" :error="error" @retry="reload">
      <template #cell-active="{ row }"><StatusChip :tone="row.active ? 'success' : 'neutral'" :label="row.active ? 'Current' : 'Not current'" /></template>
      <template #cell-actions="{ row }"><button class="btn-icon" aria-label="Edit" @click="openDialog(row)"><Pencil class="size-4" /></button></template>
    </DataTable>
    <AcademicDialog v-model:open="dialog.open" :kind="dialog.kind" :item="dialog.item" :departments="data?.departments || []" @saved="saved" />
    <ConfirmDialog v-model:open="confirm.open" :title="confirm.title || ''" confirm-label="Delete" tone="danger" :action="confirm.run">{{ confirm.text }}</ConfirmDialog>
  </template>
</template>
