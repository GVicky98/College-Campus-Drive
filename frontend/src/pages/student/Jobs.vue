<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Briefcase } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import Pagination from '@/components/ui/Pagination.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import JobCard from '@/components/JobCard.vue'
import ApplyDialog from '@/components/ApplyDialog.vue'
import { jobsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const reference = useReference().ref

const tabs = [
  { value: 'all', label: 'All jobs' }, { value: 'eligible', label: 'Eligible' }, { value: 'not_eligible', label: 'Not eligible' },
  { value: 'saved', label: 'Saved' }, { value: 'applied', label: 'Applied' },
]
const f = reactive({ tab: 'all', q: route.query.q || '', dept: '', minCgpa: '', location: '', type: '', deadlineDays: '', sort: 'deadline', page: 1 })
const filtersActive = computed(() => Boolean(f.q || f.dept || f.minCgpa || f.location || f.type || f.deadlineDays))

// The top-bar search navigates here with ?q=...
watch(() => route.query.q, (q) => { f.q = q || '' })
watch(() => [f.tab, f.q, f.dept, f.minCgpa, f.location, f.type, f.deadlineDays, f.sort], () => { f.page = 1 })
watch(() => f.q, (q) => router.replace({ query: q ? { q } : {} }))

const { data, loading, error, reload } = useAsync(() => jobsApi.list({ ...f, pageSize: 9 }), { watch: f })

function clear() {
  Object.assign(f, { q: '', dept: '', minCgpa: '', location: '', type: '', deadlineDays: '' })
}
async function toggleSave(view) {
  try {
    const { saved } = await jobsApi.toggleSave(view.job.id)
    view.saved = saved
    toast.success(saved ? 'Saved to your list' : 'Removed from saved')
    if (f.tab === 'saved') reload()
  } catch (e) { toast.error(e.message) }
}

const applyOpen = ref(false)
const applying = ref(null)
function openApply(view) { applying.value = view; applyOpen.value = true }

const emptyText = computed(() => {
  if (filtersActive.value) return ['No jobs match these filters', 'Try removing a filter.']
  if (f.tab === 'saved') return ['No saved jobs', 'Use the bookmark on a job to keep it here.']
  if (f.tab === 'applied') return ['No applications yet', 'Jobs you apply to appear here.']
  return ['No jobs right now', 'New openings appear here as soon as the placement cell publishes them.']
})
</script>

<template>
  <PageHeader title="Jobs & Opportunities" subtitle="Openings published by the placement cell, checked against your eligibility." />
  <Tabs v-model="f.tab" :tabs="tabs" />

  <div class="mb-4 flex flex-wrap items-center gap-3" role="search">
    <SearchInput v-model="f.q" placeholder="Search title, company or skill" />
    <SelectFilter v-model="f.dept" label="Department" :options="reference?.departments || []" />
    <SelectFilter v-model="f.minCgpa" label="CGPA required up to" :options="['6.0', '6.5', '7.0', '7.5', '8.0', '8.5', '9.0']" all-label="Any" />
    <input v-model.lazy="f.location" class="input w-36 py-1.5" placeholder="Location" aria-label="Location" />
    <SelectFilter v-model="f.type" label="Type" :options="['Full-time', 'Internship', 'Internship + PPO']" />
    <SelectFilter v-model="f.deadlineDays" label="Deadline" :options="[{ value: 3, label: 'Within 3 days' }, { value: 7, label: 'Within 7 days' }, { value: 14, label: 'Within 14 days' }]" all-label="Any time" />
    <SelectFilter v-model="f.sort" label="Sort" :options="[{ value: 'deadline', label: 'Deadline' }, { value: 'relevance', label: 'Best match' }, { value: 'recent', label: 'Newest' }]" all-label="Deadline" />
    <button v-if="filtersActive" class="btn btn-ghost btn-sm" @click="clear">Clear filters</button>
  </div>

  <ErrorState v-if="error && !data" :error="error" @retry="reload" />
  <div v-else-if="loading && !data" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
    <div v-for="i in 6" :key="i" class="card h-64 p-4"><div class="skeleton h-full" /></div>
  </div>
  <template v-else-if="data">
    <div v-if="!data.items.length" class="card">
      <EmptyState :icon="Briefcase" :title="emptyText[0]" :message="emptyText[1]">
        <button v-if="filtersActive" class="btn btn-secondary" @click="clear">Clear filters</button>
      </EmptyState>
    </div>
    <div v-else class="grid gap-4 transition-opacity md:grid-cols-2 xl:grid-cols-3" :class="loading && 'opacity-60'">
      <JobCard v-for="v in data.items" :key="v.job.id" :view="v" show-save :detail-to="`/student/jobs/${v.job.id}`"
        @toggle-save="toggleSave" @apply="openApply" />
    </div>
    <div v-if="data.total > data.pageSize" class="card mt-4">
      <Pagination :page="f.page" :page-size="data.pageSize" :total="data.total" @change="f.page = $event" />
    </div>
  </template>

  <ApplyDialog v-model:open="applyOpen" :view="applying" @applied="reload" />
</template>
