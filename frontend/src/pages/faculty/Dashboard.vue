<script setup>
import { computed, reactive } from 'vue'
import { Award, Briefcase, Building2, ClipboardList, Gift, ListChecks, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ChartCard from '@/components/charts/ChartCard.vue'
import { reportsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useBase } from '@/composables/useBase'
import { useReference } from '@/composables/useReference'
import { daysUntil, formatDateTime, formatShortDate, timeAgo } from '@/utils/format'

const base = useBase()
const reference = useReference().ref
const f = reactive({ dept: '', graduationYear: '', companyId: '', days: '' })
const { data, loading, error, reload } = useAsync(() => reportsApi.facultyDashboard(f), { watch: f })
const active = computed(() => Object.values(f).some(Boolean))
const clear = () => Object.assign(f, { dept: '', graduationYear: '', companyId: '', days: '' })

const deptSeries = computed(() => [
  { name: 'Placed', values: data.value?.deptChart.map((d) => d.placed) || [] },
  { name: 'Not yet placed', values: data.value?.deptChart.map((d) => d.notPlaced) || [] },
])
const statusData = computed(() => (data.value?.statusDist || []).filter((s) => s.count))
</script>

<template>
  <PageHeader title="Placement dashboard" subtitle="Live picture of drives, applicants and offers.">
    <template #actions><RouterLink :to="`${base}/applications`" class="btn btn-primary">Review applications</RouterLink></template>
  </PageHeader>

  <div class="mb-5 flex flex-wrap items-center gap-3">
    <SelectFilter v-model="f.dept" label="Department" :options="reference?.departments || []" />
    <SelectFilter v-model="f.graduationYear" label="Batch" :options="data?.graduationYears || []" />
    <SelectFilter v-model="f.companyId" label="Company" :options="reference?.companies || []" />
    <SelectFilter v-model="f.days" label="Applications in" all-label="All time"
      :options="[{ value: 7, label: 'Last 7 days' }, { value: 30, label: 'Last 30 days' }, { value: 90, label: 'Last 90 days' }, { value: 365, label: 'Last year' }]" />
    <button v-if="active" class="btn btn-ghost btn-sm" @click="clear">Clear filters</button>
  </div>

  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" :rows="8" @retry="reload">
    <div v-if="data" class="space-y-6" :class="loading && 'opacity-60'">
      <div class="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        <MetricCard label="Companies" :value="data.metrics.totalCompanies" :icon="Building2" :to="`${base}/companies`" />
        <MetricCard label="Active jobs" :value="data.metrics.activeJobs" :icon="Briefcase" tone="purple" :to="`${base}/jobs`" />
        <MetricCard label="Applications" :value="data.metrics.totalApplications" :icon="ClipboardList" tone="slate" :to="`${base}/applications`" />
        <MetricCard label="Eligible students" hint="For ≥1 open job" :value="data.metrics.eligibleStudents" :icon="Users" tone="green" :to="`${base}/students`" />
        <MetricCard label="Shortlisted" :value="data.metrics.shortlisted" :icon="ListChecks" tone="amber" />
        <MetricCard label="Selected" :value="data.metrics.selected" :icon="Award" tone="green" />
        <MetricCard label="Offers" :value="data.metrics.offers" :icon="Gift" tone="red" :to="`${base}/offers`" />
      </div>

      <div class="grid gap-6 lg:grid-cols-5">
        <ChartCard class="lg:col-span-3" title="Department-wise placement" type="stacked"
          :labels="data.deptChart.map((d) => d.dept)" :series="deptSeries" />
        <ChartCard class="lg:col-span-2" title="Application status" type="donut"
          :labels="statusData.map((s) => s.label)" :series="[{ name: 'Applications', values: statusData.map((s) => s.count) }]" />
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Upcoming hiring drives">
          <template #actions><RouterLink :to="`${base}/drives`" class="link text-xs">All drives</RouterLink></template>
          <p v-if="!data.upcomingDrives.length" class="text-sm text-muted">No upcoming drives.</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="v in data.upcomingDrives" :key="v.job.id" class="flex items-center gap-3 py-2.5">
              <div class="min-w-0 flex-1">
                <RouterLink :to="`${base}/jobs/${v.job.id}`" class="block truncate text-sm font-medium hover:underline">{{ v.company.name }} — {{ v.job.title }}</RouterLink>
                <p class="text-xs text-muted">{{ formatDateTime(v.job.driveDate) }} · {{ v.applicantCount }} applicants</p>
              </div>
              <StatusChip tone="info" :label="`${daysUntil(v.job.driveDate)}d`" />
            </li>
          </ul>
        </SectionCard>
        <SectionCard title="Upcoming interviews">
          <template #actions><RouterLink :to="`${base}/interviews`" class="link text-xs">Schedule</RouterLink></template>
          <p v-if="!data.upcomingInterviews.length" class="text-sm text-muted">No interviews scheduled.</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="i in data.upcomingInterviews" :key="i.id" class="flex items-center gap-3 py-2.5">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ i.round }} — {{ i.company }}</p>
                <p class="text-xs text-muted">{{ formatDateTime(i.at) }} · {{ i.candidates }} candidate(s)</p>
              </div>
              <StatusChip :tone="i.notified ? 'success' : 'warning'" :label="i.notified ? 'Notified' : 'Not notified'" />
            </li>
          </ul>
        </SectionCard>
        <SectionCard title="Jobs nearing deadline">
          <p v-if="!data.nearingDeadline.length" class="text-sm text-muted">No deadlines in the next few days.</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="v in data.nearingDeadline" :key="v.job.id" class="flex items-center justify-between gap-3 py-2.5 text-sm">
              <RouterLink :to="`${base}/jobs/${v.job.id}`" class="truncate hover:underline">{{ v.company.name }} — {{ v.job.title }}</RouterLink>
              <span class="shrink-0 text-xs text-red-700">closes {{ formatShortDate(v.job.deadline) }}</span>
            </li>
          </ul>
        </SectionCard>
        <SectionCard title="Recent applications">
          <p v-if="!data.recentApplications.length" class="text-sm text-muted">No applications yet.</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="a in data.recentApplications" :key="a.applicationId" class="flex items-center gap-3 py-2.5">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ a.student }} <span class="font-normal text-muted">· {{ a.studentCode }}</span></p>
                <p class="truncate text-xs text-muted">{{ a.company }} — {{ a.job }} · {{ timeAgo(a.at) }}</p>
              </div>
              <StatusChip kind="application" :value="a.status" />
            </li>
          </ul>
        </SectionCard>
      </div>

      <SectionCard title="Recent placement activity">
        <p v-if="!data.activity.length" class="text-sm text-muted">No activity yet.</p>
        <ul v-else class="divide-y divide-line">
          <li v-for="(a, i) in data.activity" :key="i" class="flex flex-wrap items-center gap-3 py-2.5 text-sm">
            <StatusChip kind="application" :value="a.status" />
            <span class="min-w-0 flex-1 truncate">{{ a.student }} — {{ a.company }} {{ a.job }}</span>
            <span class="text-xs text-muted">{{ timeAgo(a.at) }}</span>
          </li>
        </ul>
      </SectionCard>
    </div>
  </AsyncBlock>
</template>
