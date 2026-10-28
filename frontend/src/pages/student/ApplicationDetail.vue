<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ApplicationTimeline from '@/components/ApplicationTimeline.vue'
import EligibilityReasons from '@/components/EligibilityReasons.vue'
import { applicationsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useToast } from '@/composables/toast'
import { formatDate, formatDateTime, formatPackage, timeAgo } from '@/utils/format'

const route = useRoute()
const toast = useToast()
const { data: d, loading, error, reload } = useAsync(() => applicationsApi.get(route.params.applicationId))
const withdrawOpen = ref(false)
const canWithdraw = computed(() => ['applied', 'shortlisted', 'interview'].includes(d.value?.application.status))
const history = computed(() => [...(d.value?.application.history || [])].reverse())

async function withdraw() {
  await applicationsApi.withdraw(d.value.application.id)
  toast.success('Application withdrawn')
  reload()
}
</script>

<template>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!d" :rows="10" @retry="reload">
    <template v-if="d">
      <PageHeader :title="`${d.company.name} — ${d.job.title}`"
        :crumbs="[{ label: 'My Applications', to: '/student/applications' }, { label: d.job.title }]">
        <template #subtitle>
          <span class="flex flex-wrap items-center gap-2">
            <StatusChip kind="application" :value="d.application.status" />
            Applied {{ formatDate(d.application.appliedAt) }} · updated {{ timeAgo(d.application.updatedAt) }}
          </span>
        </template>
        <template #actions>
          <RouterLink :to="`/student/jobs/${d.job.id}`" class="btn btn-secondary">View job</RouterLink>
          <button v-if="canWithdraw" class="btn btn-danger" @click="withdrawOpen = true">Withdraw</button>
        </template>
      </PageHeader>

      <div class="grid gap-6 lg:grid-cols-3">
        <div class="space-y-6 lg:col-span-2">
          <SectionCard title="Progress"><ApplicationTimeline :application="d.application" /></SectionCard>

          <SectionCard v-if="d.offer" title="Offer">
            <div class="flex flex-wrap items-center gap-6 text-sm">
              <StatusChip kind="offer" :value="d.offer.status" />
              <span><span class="text-muted">Package</span> <b>{{ formatPackage(d.offer.ctcLpa) }}</b></span>
              <span><span class="text-muted">Respond by</span> <b>{{ formatDate(d.offer.acceptBy) }}</b></span>
              <RouterLink to="/student/offers" class="btn btn-secondary btn-sm ml-auto">Open offers</RouterLink>
            </div>
          </SectionCard>

          <SectionCard title="Interview schedule">
            <p v-if="!d.interviews.length" class="text-sm text-muted">No interviews scheduled yet.</p>
            <ul v-else class="divide-y divide-line">
              <li v-for="i in d.interviews" :key="i.id" class="flex flex-wrap items-center gap-3 py-2.5 text-sm">
                <span class="font-medium">{{ i.round }}</span>
                <span class="text-muted">{{ formatDateTime(i.at) }} · {{ i.durationMins }} min · {{ i.location }}</span>
                <StatusChip class="ml-auto" kind="interview" :value="i.status" />
              </li>
            </ul>
          </SectionCard>

          <SectionCard title="Status history">
            <ul class="space-y-3">
              <li v-for="(h, i) in history" :key="i" class="flex flex-wrap items-center gap-2 text-sm">
                <StatusChip kind="application" :value="h.status" />
                <span class="text-muted">{{ formatDateTime(h.at) }} · by {{ h.by }}</span>
                <span v-if="h.note" class="w-full text-slate-700 sm:w-auto">— {{ h.note }}</span>
              </li>
            </ul>
          </SectionCard>
        </div>

        <div class="space-y-6">
          <SectionCard v-if="d.application.eligibilitySnapshot" title="Eligibility at application">
            <EligibilityReasons :result="d.application.eligibilitySnapshot" show-time />
          </SectionCard>
          <SectionCard title="Job details">
            <dl class="space-y-2 text-sm">
              <div class="flex justify-between gap-3"><dt class="text-muted">Package</dt><dd>{{ formatPackage(d.job.ctcLpa, d.job.stipendPerMonth) }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Location</dt><dd>{{ d.job.location }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-muted">Type</dt><dd>{{ d.job.type }}</dd></div>
              <div v-if="d.job.driveDate" class="flex justify-between gap-3"><dt class="text-muted">Drive</dt><dd>{{ formatDateTime(d.job.driveDate) }}</dd></div>
            </dl>
          </SectionCard>
          <SectionCard title="Related notifications">
            <p v-if="!d.notifications.length" class="text-sm text-muted">None.</p>
            <ul v-else class="space-y-3">
              <li v-for="n in d.notifications" :key="n.id" class="text-sm">
                <p class="font-medium">{{ n.title }}</p><p class="text-xs text-muted">{{ n.body }} · {{ timeAgo(n.at) }}</p>
              </li>
            </ul>
          </SectionCard>
        </div>
      </div>

      <ConfirmDialog v-model:open="withdrawOpen" title="Withdraw application?" confirm-label="Withdraw" tone="danger" :action="withdraw">
        You are withdrawing from <b>{{ d.company.name }} — {{ d.job.title }}</b>. The placement cell will see this in your history.
      </ConfirmDialog>
    </template>
  </AsyncBlock>
</template>
