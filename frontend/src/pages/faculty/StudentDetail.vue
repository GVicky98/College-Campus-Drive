<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { studentsApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useBase } from '@/composables/useBase'
import { useToast } from '@/composables/toast'
import { formatDate, formatNextAction, formatPackage } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const base = useBase()
const toast = useToast()
const { data: d, loading, error, reload } = useAsync(() => studentsApi.get(route.params.studentId))
const s = computed(() => d.value?.student)
const canVerify = computed(() => auth.can('students.edit') && s.value?.academic.cgpa !== undefined && !s.value.academic.cgpaVerified)
const verifyOpen = ref(false)
async function verify() {
  await studentsApi.verifyCgpa(s.value.id)
  toast.success('CGPA verified — the student was notified')
  reload()
}
const appCols = [{ key: 'job', label: 'Job' }, { key: 'stage', label: 'Stage' }, { key: 'applied', label: 'Applied', hide: 'sm' }, { key: 'next', label: 'Next step', hide: 'md' }]
const offerCols = [{ key: 'company', label: 'Company' }, { key: 'package', label: 'Package' }, { key: 'status', label: 'Status' }, { key: 'by', label: 'Respond by', hide: 'sm' }]
const listBase = computed(() => (base.value === '/admin' ? '/admin/students' : `${base.value}/students`))
</script>

<template>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!d" :rows="8" @retry="reload">
    <template v-if="s">
      <PageHeader :title="s.name" :crumbs="[{ label: 'Students', to: listBase }, { label: s.name }]">
        <template #subtitle><span class="flex flex-wrap items-center gap-2">{{ s.studentCode }} · {{ s.departmentName }} · Batch {{ s.graduationYear }}
          <StatusChip kind="placement" :value="s.placementStatus" /></span></template>
        <template #actions><button v-if="canVerify" class="btn btn-primary" @click="verifyOpen = true">Verify CGPA</button></template>
      </PageHeader>
      <p v-if="s.academic.cgpa === undefined" class="alert alert-warning mb-4">No CGPA on file. The student will show as “profile incomplete” for every job.</p>
      <p v-else-if="!s.academic.cgpaVerified" class="alert alert-info mb-4">The CGPA is not verified yet, so the student cannot apply until it is.</p>

      <div class="mb-6 grid gap-6 lg:grid-cols-2">
        <SectionCard title="Profile">
          <dl class="grid gap-3 text-sm sm:grid-cols-2">
            <div><dt class="text-xs text-muted">E-mail</dt><dd class="break-all">{{ s.email }}</dd></div>
            <div><dt class="text-xs text-muted">Phone</dt><dd>{{ s.phone || '—' }}</dd></div>
            <div><dt class="text-xs text-muted">Degree · year</dt><dd>{{ s.degree || '—' }} · Year {{ s.currentYear }}</dd></div>
            <div><dt class="text-xs text-muted">Profile completion</dt><dd>{{ s.profileCompletion }}%</dd></div>
            <div><dt class="text-xs text-muted">Resume</dt><dd>{{ s.resumeFile || '—' }}</dd></div>
            <div><dt class="text-xs text-muted">Portfolio</dt><dd><a v-if="s.portfolioUrl" :href="s.portfolioUrl" target="_blank" rel="noopener" class="link break-all">{{ s.portfolioUrl }}</a><span v-else>—</span></dd></div>
          </dl>
          <p v-if="d.masked" class="hint mt-3">Phone numbers are partly hidden for faculty.</p>
        </SectionCard>
        <SectionCard title="Academics">
          <dl class="grid gap-3 text-sm sm:grid-cols-3">
            <div><dt class="text-xs text-muted">CGPA</dt><dd class="text-lg font-semibold">{{ s.academic.cgpa?.toFixed(2) ?? '—' }}</dd>
              <StatusChip :tone="s.academic.cgpaVerified ? 'success' : 'warning'" :label="s.academic.cgpaVerified ? 'Verified' : 'Unverified'" /></div>
            <div><dt class="text-xs text-muted">Active arrears</dt><dd>{{ s.academic.activeArrears }}</dd></div>
            <div><dt class="text-xs text-muted">Arrear history</dt><dd>{{ s.academic.arrearHistory }}</dd></div>
          </dl>
          <div class="mt-4 space-y-2 text-sm">
            <p><span class="text-muted">Skills:</span> {{ s.skills.join(', ') || '—' }}</p>
            <p><span class="text-muted">Interests:</span> {{ s.interests.join(', ') || '—' }}</p>
            <p><span class="text-muted">Preferred roles:</span> {{ s.preferredRoles.join(', ') || '—' }}</p>
          </div>
        </SectionCard>
      </div>
      <h2 class="mb-3 text-base">Applications</h2>
      <DataTable class="mb-6" :columns="appCols" :rows="d.applications" :row-key="(r) => r.application.id" empty-title="No applications">
        <template #cell-job="{ row }">{{ row.company.name }} — {{ row.job.title }}</template>
        <template #cell-stage="{ row }"><StatusChip kind="application" :value="row.application.status" /></template>
        <template #cell-applied="{ row }">{{ formatDate(row.application.appliedAt) }}</template>
        <template #cell-next="{ row }"><span class="text-muted">{{ formatNextAction(row.nextAction) }}</span></template>
      </DataTable>
      <h2 class="mb-3 text-base">Offers</h2>
      <DataTable :columns="offerCols" :rows="d.offers" :row-key="(r) => r.offer.id" empty-title="No offers">
        <template #cell-company="{ row }">{{ row.company.name }} — {{ row.job.title }}</template>
        <template #cell-package="{ row }">{{ formatPackage(row.offer.ctcLpa) }}</template>
        <template #cell-status="{ row }"><StatusChip kind="offer" :value="row.offer.status" /></template>
        <template #cell-by="{ row }">{{ formatDate(row.offer.acceptBy) }}</template>
      </DataTable>
      <ConfirmDialog v-model:open="verifyOpen" title="Verify CGPA?" confirm-label="Verify" :action="verify">
        Confirm that <b>{{ s.name }}</b>'s CGPA of <b>{{ s.academic.cgpa?.toFixed(2) }}</b> matches the official record. The student is notified.
      </ConfirmDialog>
    </template>
  </AsyncBlock>
</template>
