<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import Students from '@/pages/faculty/Students.vue'
import { usersApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tab = computed({ get: () => (route.path.endsWith('/faculty') ? 'faculty' : 'students'), set: (v) => router.replace(`/admin/${v}`) })
const faculty = useAsync(() => (auth.can('users.manage') ? usersApi.list({ role: 'faculty', pageSize: 50 }) : Promise.resolve({ items: [] })))
const cols = [{ key: 'name', label: 'Name' }, { key: 'email', label: 'E-mail', hide: 'sm' }, { key: 'departmentCode', label: 'Department' },
  { key: 'status', label: 'Status' }, { key: 'last', label: 'Last sign-in', hide: 'md' }]
</script>

<template>
  <PageHeader title="Students & faculty" subtitle="Everyone in the placement process." />
  <Tabs v-model="tab" :tabs="[{ value: 'students', label: 'Students' }, { value: 'faculty', label: 'Faculty' }]" />
  <Students v-if="tab === 'students'" embedded />
  <template v-else>
    <p class="alert alert-info mb-4">Faculty accounts are read-only here. <RouterLink v-if="auth.can('users.manage')" to="/admin/users?role=faculty" class="underline">Manage them in User management.</RouterLink></p>
    <DataTable :columns="cols" :rows="faculty.data.value?.items || []" :loading="faculty.loading.value" :error="faculty.error.value" empty-title="No faculty accounts">
      <template #cell-name="{ row }"><span class="font-medium">{{ row.name }}</span></template>
      <template #cell-departmentCode="{ row }">{{ row.departmentCode || '—' }}</template>
      <template #cell-status="{ row }"><StatusChip kind="user" :value="row.status" /></template>
      <template #cell-last="{ row }">{{ formatDateTime(row.lastLoginAt) }}</template>
    </DataTable>
  </template>
</template>
