<script setup>
import { reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import { adminApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const f = reactive({ actor: '', resource: '', action: '', result: route.query.result || '', from: '', to: '', page: 1 })
watch(() => [f.actor, f.resource, f.action, f.result, f.from, f.to], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => adminApi.auditLogs({ ...f, pageSize: 12 }), { watch: f })
const columns = [
  { key: 'at', label: 'Timestamp' }, { key: 'actor', label: 'Actor' }, { key: 'action', label: 'Action' },
  { key: 'resource', label: 'Affected record', hide: 'md' }, { key: 'result', label: 'Result' }, { key: 'reason', label: 'Details', hide: 'lg' },
]
</script>

<template>
  <PageHeader title="Audit logs" subtitle="Every sign-in, change and refused attempt. This log is read-only and cannot be edited or deleted." />
  <DataTable :columns="columns" :rows="data?.items || []" :loading="loading" :error="error" :total="data?.total" :page="f.page" :page-size="12"
    empty-title="No entries match" @page="f.page = $event" @retry="reload">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <input v-model.lazy="f.actor" class="input w-40 py-1.5" placeholder="User" aria-label="User" />
        <input v-model.lazy="f.resource" class="input w-40 py-1.5" placeholder="Record" aria-label="Record" />
        <SelectFilter v-model="f.action" label="Action" :options="data?.meta.actions || []" />
        <SelectFilter v-model="f.result" label="Result" :options="[{ value: 'success', label: 'Success' }, { value: 'denied', label: 'Denied' }, { value: 'failed', label: 'Failed' }]" />
        <label class="flex items-center gap-2 text-xs text-muted">From <input v-model="f.from" type="date" class="input w-auto py-1.5" /></label>
        <label class="flex items-center gap-2 text-xs text-muted">To <input v-model="f.to" type="date" class="input w-auto py-1.5" /></label>
      </div>
    </template>
    <template #cell-at="{ row }"><span class="whitespace-nowrap">{{ formatDateTime(row.at) }}</span></template>
    <template #cell-actor="{ row }">{{ row.actor }}<span class="block text-xs text-muted">{{ row.actorRole }}</span></template>
    <template #cell-action="{ row }"><code class="rounded bg-slate-100 px-1.5 text-xs">{{ row.action }}</code></template>
    <template #cell-result="{ row }"><StatusChip kind="result" :value="row.result" /></template>
    <template #cell-reason="{ row }"><span class="text-xs text-muted">{{ row.reason || '—' }}</span></template>
  </DataTable>
</template>
