<script setup>
import { computed } from 'vue'
import { BadgeCheck, Bot, Briefcase, CalendarDays, ClipboardList, Gift } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import JobCard from '@/components/JobCard.vue'
import { studentApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { daysUntil, formatCgpa, formatDateTime, timeAgo } from '@/utils/format'

const auth = useAuthStore()
const { data, loading, error, reload } = useAsync(() => studentApi.dashboard())

const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
})
const firstName = computed(() => auth.user?.name.split(' ')[0])
</script>

<template>
  <PageHeader :title="`${greeting}, ${firstName}`" subtitle="Here's where your placements stand today.">
    <template #actions>
      <RouterLink to="/student/assistant" class="btn btn-accent"><Bot class="size-4" /> Ask the AI assistant</RouterLink>
    </template>
  </PageHeader>

  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" :rows="8" @retry="reload">
    <div v-if="data" class="space-y-6">
      <div class="grid gap-4 lg:grid-cols-3">
        <div class="card p-5 lg:col-span-1">
          <p class="text-sm font-medium">Profile completion</p>
          <p class="mt-1 text-3xl font-semibold">{{ data.student.profileCompletion }}%</p>
          <div class="mt-3 h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full bg-brand-600" :style="{ width: data.student.profileCompletion + '%' }" /></div>
          <RouterLink to="/student/profile" class="btn btn-secondary btn-sm mt-4">
            {{ data.student.profileCompletion < 100 ? 'Complete profile' : 'View profile' }}
          </RouterLink>
        </div>
        <div class="card p-5 lg:col-span-2">
          <p class="text-sm font-medium">Academic summary</p>
          <div class="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p class="text-xs text-muted">CGPA</p>
              <p class="flex items-center gap-1.5 text-xl font-semibold">{{ formatCgpa(data.student.academic.cgpa) }}
                <BadgeCheck v-if="data.student.academic.cgpaVerified" class="size-4 text-green-600" aria-label="Verified" />
              </p>
              <StatusChip :tone="data.student.academic.cgpaVerified ? 'success' : 'warning'" :label="data.student.academic.cgpaVerified ? 'Verified' : 'Unverified'" />
            </div>
            <div><p class="text-xs text-muted">Department</p><p class="font-medium">{{ data.student.departmentName }}</p></div>
            <div><p class="text-xs text-muted">Year · degree</p><p class="font-medium">Year {{ data.student.currentYear }} · {{ data.student.degree || '—' }}</p></div>
            <div><p class="text-xs text-muted">Batch</p><p class="font-medium">{{ data.student.graduationYear }}</p></div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Eligible jobs" :value="data.metrics.eligibleJobs" :icon="Briefcase" to="/student/jobs" />
        <MetricCard label="Active applications" :value="data.metrics.activeApplications" :icon="ClipboardList" tone="purple" to="/student/applications" />
        <MetricCard label="Upcoming events" :value="data.metrics.upcoming" :icon="CalendarDays" tone="amber" />
        <MetricCard label="Offers received" :value="data.metrics.offers" :icon="Gift" tone="green" to="/student/offers" />
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Upcoming interviews & drives">
          <p v-if="!data.events.length" class="text-sm text-muted">Nothing scheduled yet.</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="e in data.events" :key="e.id" class="flex items-center gap-3 py-2.5">
              <span class="flex size-9 items-center justify-center rounded-lg" :class="e.kind === 'interview' ? 'bg-violet-50 text-violet-700' : 'bg-blue-50 text-blue-700'">
                <CalendarDays class="size-4" />
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ e.title }}</p>
                <p class="text-xs text-muted">{{ e.sub }} · {{ formatDateTime(e.at) }}<span v-if="e.location"> · {{ e.location }}</span></p>
              </div>
              <StatusChip :tone="e.kind === 'interview' ? 'purple' : 'info'" :label="e.kind === 'interview' ? 'Interview' : 'Drive'" />
            </li>
          </ul>
        </SectionCard>

        <SectionCard title="Upcoming deadlines">
          <p v-if="!data.deadlines.length" class="text-sm text-muted">No open deadlines for you right now.</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="v in data.deadlines" :key="v.job.id" class="flex items-center gap-3 py-2.5">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ v.job.title }}</p>
                <p class="text-xs text-muted">{{ v.company.name }}</p>
              </div>
              <RouterLink :to="`/student/jobs/${v.job.id}`" class="btn btn-secondary btn-sm"
                :class="daysUntil(v.job.deadline) <= 3 && 'border-red-300 text-red-700'">{{ daysUntil(v.job.deadline) }}d left</RouterLink>
            </li>
          </ul>
        </SectionCard>
      </div>

      <div>
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-base">Recommended for you</h2>
          <RouterLink to="/student/jobs" class="link text-sm">All jobs</RouterLink>
        </div>
        <p v-if="!data.recommended.length" class="card p-5 text-sm text-muted">No recommendations yet. Add skills to your profile to get better matches.</p>
        <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <JobCard v-for="v in data.recommended" :key="v.job.id" :view="v" compact :detail-to="`/student/jobs/${v.job.id}`" />
        </div>
      </div>

      <SectionCard title="Recent application activity">
        <p v-if="!data.activity.length" class="text-sm text-muted">No activity yet. Apply to a job to get started.</p>
        <ul v-else class="divide-y divide-line">
          <li v-for="(a, i) in data.activity" :key="i" class="flex flex-wrap items-center gap-3 py-2.5">
            <StatusChip kind="application" :value="a.status" />
            <RouterLink :to="`/student/applications/${a.applicationId}`" class="min-w-0 flex-1 truncate text-sm hover:underline">{{ a.text }}</RouterLink>
            <span class="text-xs text-muted">{{ timeAgo(a.at) }}</span>
          </li>
        </ul>
      </SectionCard>
    </div>
  </AsyncBlock>
</template>
