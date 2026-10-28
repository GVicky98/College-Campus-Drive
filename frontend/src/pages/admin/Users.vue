<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { KeyRound, Pencil, Plus, Power, Upload } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import UserDialog from './parts/UserDialog.vue'
import ImportDialog from './parts/ImportDialog.vue'
import { usersApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { formatDate } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const toast = useToast()
const reference = useReference().ref
const f = reactive({ q: route.query.q || '', role: route.query.role || '', status: '', dept: '', page: 1 })
watch(() => route.query.q, (q) => { f.q = q || '' })
watch(() => [f.q, f.role, f.status, f.dept], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => usersApi.list({ ...f, pageSize: 10 }), { watch: f })
const columns = [
  { key: 'name', label: 'Name' }, { key: 'email', label: 'E-mail', hide: 'md' }, { key: 'userCode', label: 'User ID', hide: 'sm' },
  { key: 'role', label: 'Role' }, { key: 'dept', label: 'Department', hide: 'lg' }, { key: 'status', label: 'Status' },
  { key: 'created', label: 'Created', hide: 'lg' }, { key: 'actions', label: '', align: 'right' },
]
const ROLES = [{ value: 'student', label: 'Student' }, { value: 'faculty', label: 'Faculty' }, { value: 'admin', label: 'Admin' }]
const STATUSES = [{ value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }, { value: 'invited', label: 'Invited' }]

const dialogOpen = ref(false)
const editing = ref(null)
const importOpen = ref(false)
const confirm = ref({ open: false })
const isSelf = (u) => u.id === auth.user.id

function ask(kind, u) {
  confirm.value = kind === 'reset'
    ? { open: true, title: 'Send a password reset?', label: 'Create reset link', tone: 'primary', text: `A one-time reset link is created for ${u.email}.`,
        run: async () => toast.success((await usersApi.resetPassword(u.id)).message) }
    : { open: true, title: u.status === 'inactive' ? 'Activate account?' : 'Deactivate account?', label: u.status === 'inactive' ? 'Activate' : 'Deactivate',
        tone: u.status === 'inactive' ? 'primary' : 'danger',
        text: u.status === 'inactive' ? `${u.name} can sign in again.` : `${u.name} is signed out everywhere and cannot sign in. Their records are kept.`,
        run: async () => { await usersApi.setStatus(u.id, u.status === 'inactive' ? 'active' : 'inactive'); toast.success('Account updated'); reload() } }
}
</script>

<template>
  <PageHeader title="User management" subtitle="Invite, edit and deactivate accounts. Accounts are never deleted.">
    <template #actions>
      <button class="btn btn-secondary" @click="importOpen = true"><Upload class="size-4" /> Import students</button>
      <button class="btn btn-primary" @click="editing = null; dialogOpen = true"><Plus class="size-4" /> Add user</button>
    </template>
  </PageHeader>
  <DataTable :columns="columns" :rows="data?.items || []" :loading="loading" :error="error" :total="data?.total" :page="f.page" :page-size="10"
    empty-title="No users match" @page="f.page = $event" @retry="reload">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <SearchInput v-model="f.q" placeholder="Name, e-mail or user ID" />
        <SelectFilter v-model="f.role" label="Role" :options="ROLES" />
        <SelectFilter v-model="f.status" label="Status" :options="STATUSES" />
        <SelectFilter v-model="f.dept" label="Department" :options="reference?.departments || []" />
      </div>
    </template>
    <template #cell-name="{ row }"><span class="font-medium">{{ row.name }}</span><span v-if="isSelf(row)" class="ml-1 text-xs text-muted">(you)</span></template>
    <template #cell-role="{ row }"><StatusChip kind="role" :value="row.role" /></template>
    <template #cell-dept="{ row }">{{ row.departmentCode || '—' }}</template>
    <template #cell-status="{ row }"><StatusChip kind="user" :value="row.status" /></template>
    <template #cell-created="{ row }">{{ formatDate(row.createdAt) }}</template>
    <template #cell-actions="{ row }">
      <div class="flex justify-end">
        <button class="btn-icon" aria-label="Edit user" @click="editing = row; dialogOpen = true"><Pencil class="size-4" /></button>
        <button class="btn-icon" aria-label="Send password reset" :disabled="row.status === 'inactive'" @click="ask('reset', row)"><KeyRound class="size-4" /></button>
        <button class="btn-icon" :class="row.status !== 'inactive' && 'hover:text-red-700'" :aria-label="row.status === 'inactive' ? 'Activate' : 'Deactivate'"
          :disabled="isSelf(row) || row.status === 'invited'" @click="ask('status', row)"><Power class="size-4" /></button>
      </div>
    </template>
  </DataTable>
  <UserDialog v-model:open="dialogOpen" :user="editing" @saved="toast.success(editing ? 'User updated' : 'User invited'); reload()" />
  <ImportDialog v-model:open="importOpen" @imported="reload" />
  <ConfirmDialog v-model:open="confirm.open" :title="confirm.title || ''" :confirm-label="confirm.label" :tone="confirm.tone" :action="confirm.run">{{ confirm.text }}</ConfirmDialog>
</template>
