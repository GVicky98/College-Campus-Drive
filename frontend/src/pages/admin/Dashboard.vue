<script setup>
import { Briefcase, Building2, ClipboardList, Gift, GraduationCap, UserCog, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import { adminApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { timeAgo } from '@/utils/format'

const auth = useAuthStore()
const { data, loading, error, reload } = useAsync(() => adminApi.dashboard())
const ALERT = { error: 'alert-error', warning: 'alert-warning', info: 'alert-info' }
</script>

<template>
  <PageHeader title="Administration" subtitle="Accounts, configuration and system health." />
  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" :rows="8" @retry="reload">
    <div v-if="data" class="space-y-6">
      <div class="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        <MetricCard label="Total users" :value="data.metrics.totalUsers" :icon="UserCog" :to="auth.can('users.manage') ? '/admin/users' : undefined" />
        <MetricCard label="Active students" :value="data.metrics.activeStudents" :icon="GraduationCap" tone="green" />
        <MetricCard label="Faculty accounts" :value="data.metrics.facultyAccounts" :icon="Users" tone="purple" />
        <MetricCard label="Companies" :value="data.metrics.companies" :icon="Building2" tone="slate" to="/admin/companies" />
        <MetricCard label="Active jobs" :value="data.metrics.activeJobs" :icon="Briefcase" tone="amber" to="/admin/jobs" />
        <MetricCard label="Applications" :value="data.metrics.applications" :icon="ClipboardList" />
        <MetricCard label="Total offers" :value="data.metrics.offers" :icon="Gift" tone="red" />
      </div>
      <div class="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Placement summary">
          <template #actions><RouterLink v-if="auth.can('reports.view')" to="/admin/reports" class="link text-xs">Full reports</RouterLink></template>
          <p class="text-4xl font-semibold">{{ data.placement.pct }}%</p>
          <p class="text-sm text-muted">{{ data.placement.placed }} of {{ data.placement.totalStudents }} students placed · {{ data.placement.offers }} offers, {{ data.placement.accepted }} accepted</p>
          <div class="mt-4 h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full bg-green-600" :style="{ width: data.placement.pct + '%' }" /></div>
        </SectionCard>
        <SectionCard title="System alerts">
          <p v-if="!data.alerts.length" class="text-sm text-muted">No alerts. Everything looks fine.</p>
          <ul v-else class="space-y-2">
            <li v-for="a in data.alerts" :key="a.text" class="alert items-center" :class="ALERT[a.level]">
              <span class="flex-1">{{ a.text }}</span><RouterLink v-if="a.link" :to="a.link" class="font-medium underline">View</RouterLink>
            </li>
          </ul>
        </SectionCard>
      </div>
      <SectionCard v-if="data.activity" title="Recent administrative activity">
        <template #actions><RouterLink to="/admin/audit-logs" class="link text-xs">All audit logs</RouterLink></template>
        <ul class="divide-y divide-line">
          <li v-for="e in data.activity" :key="e.id" class="flex flex-wrap items-center gap-3 py-2.5 text-sm">
            <span class="font-medium">{{ e.actor }}</span><code class="rounded bg-slate-100 px-1.5 text-xs">{{ e.action }}</code>
            <span class="min-w-0 flex-1 truncate text-muted">{{ e.resource }}<span v-if="e.reason"> — {{ e.reason }}</span></span>
            <StatusChip kind="result" :value="e.result" /><span class="text-xs text-muted">{{ timeAgo(e.at) }}</span>
          </li>
        </ul>
      </SectionCard>
    </div>
  </AsyncBlock>
</template>
