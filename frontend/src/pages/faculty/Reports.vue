<script setup>
import { computed, reactive } from 'vue'
import { Download, Gift, Handshake, Percent, Scale, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import ChartCard from '@/components/charts/ChartCard.vue'
import FunnelBars from '@/components/charts/FunnelBars.vue'
import { reportsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { downloadText } from '@/utils/format'

const toast = useToast()
const reference = useReference().ref
const f = reactive({ academicYear: '', dept: '', companyId: '', jobId: '', appStatus: '', offerStatus: '' })
const { data: r, loading, error, reload } = useAsync(() => reportsApi.placement(f), { watch: f })
const jobs = computed(() => (reference.value?.jobs || []).filter((j) => !f.companyId || j.companyId === f.companyId))
const active = computed(() => Object.values(f).some(Boolean))
const clear = () => Object.keys(f).forEach((k) => { f[k] = '' })
async function exportCsv() {
  try { downloadText('placement-offers.csv', await reportsApi.exportPlacement(f)) } catch (e) { toast.error(e.message) }
}
const APP = ['applied', 'shortlisted', 'interview', 'selected', 'offer_received', 'rejected', 'withdrawn'].map((s) => ({ value: s, label: s.replace('_', ' ') }))
const OFFER = ['received', 'accepted', 'declined', 'withdrawn'].map((s) => ({ value: s, label: s }))
</script>

<template>
  <PageHeader title="Placement reports" subtitle="Aggregated placement figures. Individual student data is never shown here.">
    <template #actions><button class="btn btn-secondary" @click="exportCsv"><Download class="size-4" /> Export offers CSV</button></template>
  </PageHeader>
  <div class="mb-5 flex flex-wrap items-center gap-3">
    <SelectFilter v-model="f.academicYear" label="Batch" :options="(reference?.graduationYears || []).map((y) => y.value)" />
    <SelectFilter v-model="f.dept" label="Department" :options="reference?.departments || []" />
    <SelectFilter v-model="f.companyId" label="Company" :options="reference?.companies || []" />
    <SelectFilter v-model="f.jobId" label="Job" :options="jobs" />
    <SelectFilter v-model="f.appStatus" label="Application" :options="APP" />
    <SelectFilter v-model="f.offerStatus" label="Offer" :options="OFFER" />
    <button v-if="active" class="btn btn-ghost btn-sm" @click="clear">Clear filters</button>
  </div>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!r" :rows="8" @retry="reload">
    <div v-if="r" class="space-y-6" :class="loading && 'opacity-60'">
      <div class="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <MetricCard label="Placement %" :value="`${r.kpis.placementPct}%`" :hint="`${r.kpis.uniqueStudentsPlaced} of ${r.kpis.totalStudents} students`" :icon="Percent" tone="green" />
        <MetricCard label="Students placed" :value="r.kpis.uniqueStudentsPlaced" :icon="Users" />
        <MetricCard label="Total offers" :value="r.kpis.totalOffers" :icon="Gift" tone="purple" />
        <MetricCard label="Accepted offers" :value="r.kpis.acceptedOffers" :icon="Handshake" tone="amber" />
        <MetricCard label="Eligible vs applied" :value="`${r.kpis.eligibleStudents} / ${r.kpis.appliedStudents}`" :icon="Scale" tone="slate" />
      </div>
      <p class="alert alert-info">Placement % counts each student once, when they have accepted at least one offer. “Eligible” means eligible for at least one open job right now.</p>
      <div class="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Offers by department" type="bar" :labels="r.offersByDept.map((d) => d.dept)"
          :series="[{ name: 'Offers', values: r.offersByDept.map((d) => d.offers) }, { name: 'Accepted', values: r.offersByDept.map((d) => d.accepted) }, { name: 'Students placed', values: r.offersByDept.map((d) => d.placedStudents) }]" />
        <ChartCard title="Company-wise offers" type="hbar" :labels="r.companyOffers.map((c) => c.company)"
          :series="[{ name: 'Offers', values: r.companyOffers.map((c) => c.offers) }, { name: 'Accepted', values: r.companyOffers.map((c) => c.accepted) }]" />
        <ChartCard title="Eligible vs applied students" type="bar" :labels="r.eligibleVsApplied.map((d) => d.dept)"
          :series="[{ name: 'Eligible', values: r.eligibleVsApplied.map((d) => d.eligible) }, { name: 'Applied', values: r.eligibleVsApplied.map((d) => d.applied) }]" />
        <SectionCard title="Application conversion funnel"><FunnelBars :stages="r.funnel" /></SectionCard>
      </div>
      <ChartCard title="Monthly hiring trend" type="line" :labels="r.monthly.map((m) => m.month)"
        :series="[{ name: 'Applications', values: r.monthly.map((m) => m.applications) }, { name: 'Offers', values: r.monthly.map((m) => m.offers) }]" />
      <SectionCard title="Application status distribution">
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
          <div v-for="s in r.statusDist" :key="s.status" class="text-center"><p class="text-2xl font-semibold">{{ s.count }}</p><p class="text-xs text-muted">{{ s.label }}</p></div>
        </div>
      </SectionCard>
    </div>
  </AsyncBlock>
</template>
