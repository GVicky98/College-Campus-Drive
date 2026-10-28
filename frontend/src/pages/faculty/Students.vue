<script setup>
import { reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BadgeCheck } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import { studentsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useBase } from '@/composables/useBase'
import { useReference } from '@/composables/useReference'

defineProps({ embedded: Boolean })
const route = useRoute()
const router = useRouter()
const base = useBase()
const reference = useReference().ref
const f = reactive({ q: route.query.q || '', dept: '', year: '', minCgpa: '', placement: '', skill: '', page: 1 })
watch(() => route.query.q, (q) => { f.q = q || '' })
watch(() => [f.q, f.dept, f.year, f.minCgpa, f.placement, f.skill], () => { f.page = 1 })
const { data, loading, error, reload } = useAsync(() => studentsApi.list({ ...f, pageSize: 10 }), { watch: f })

const columns = [
  { key: 'code', label: 'Student ID' }, { key: 'name', label: 'Name' }, { key: 'batch', label: 'Year · batch', hide: 'md' },
  { key: 'cgpa', label: 'CGPA' }, { key: 'skills', label: 'Skills', hide: 'lg' }, { key: 'profile', label: 'Profile', hide: 'lg' },
  { key: 'apps', label: 'Apps', align: 'right', hide: 'sm' }, { key: 'placement', label: 'Placement' },
]
const PLACEMENT = [{ value: 'unplaced', label: 'Unplaced' }, { value: 'in_process', label: 'In process' }, { value: 'placed', label: 'Placed' }, { value: 'opted_out', label: 'Opted out' }]
</script>

<template>
  <PageHeader v-if="!embedded" title="Students" subtitle="Academic records, skills and placement status." />
  <DataTable :columns="columns" :rows="data?.items || []" :loading="loading" :error="error" :total="data?.total" :page="f.page" :page-size="10"
    clickable empty-title="No students match" @page="f.page = $event" @retry="reload" @row-click="(r) => router.push(`${base}/students/${r.id}`)">
    <template #toolbar>
      <div class="flex flex-wrap items-center gap-3">
        <SearchInput v-model="f.q" placeholder="Name, student ID or e-mail" />
        <SelectFilter v-model="f.dept" label="Department" :options="reference?.departments || []" />
        <SelectFilter v-model="f.year" label="Batch" :options="(reference?.graduationYears || []).map((y) => y.value)" />
        <SelectFilter v-model="f.minCgpa" label="CGPA" all-label="Any" :options="[6, 7, 7.5, 8, 8.5, 9].map((v) => ({ value: v, label: `${v.toFixed(1)} and above` }))" />
        <SelectFilter v-model="f.placement" label="Placement" :options="PLACEMENT" />
        <input v-model.lazy="f.skill" class="input w-36 py-1.5" placeholder="Skill" aria-label="Skill" />
      </div>
    </template>
    <template #cell-code="{ row }"><span class="font-mono text-xs">{{ row.studentCode || '—' }}</span></template>
    <template #cell-name="{ row }"><span class="font-medium">{{ row.name }}</span><span class="block text-xs text-muted">{{ row.departmentCode }}</span></template>
    <template #cell-batch="{ row }">Year {{ row.currentYear }} · {{ row.graduationYear }}</template>
    <template #cell-cgpa="{ row }">
      <span v-if="row.academic.cgpa !== undefined" class="flex items-center gap-1">{{ row.academic.cgpa.toFixed(2) }}
        <BadgeCheck v-if="row.academic.cgpaVerified" class="size-4 text-green-600" aria-label="Verified" /></span>
      <StatusChip v-else tone="warning" label="Missing" />
    </template>
    <template #cell-skills="{ row }">
      <span class="flex flex-wrap gap-1"><span v-for="s in row.skills.slice(0, 3)" :key="s" class="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{{ s }}</span>
        <span v-if="row.skills.length > 3" class="text-xs text-muted">+{{ row.skills.length - 3 }}</span></span>
    </template>
    <template #cell-profile="{ row }">
      <div class="flex items-center gap-2"><div class="h-1.5 w-16 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-brand-600" :style="{ width: row.profileCompletion + '%' }" /></div><span class="text-xs">{{ row.profileCompletion }}%</span></div>
    </template>
    <template #cell-apps="{ row }">{{ row.applicationCount }}</template>
    <template #cell-placement="{ row }"><StatusChip kind="placement" :value="row.placementStatus" /></template>
  </DataTable>
</template>
