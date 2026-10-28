<script setup>
import { computed, ref } from 'vue'
import { Gavel, Pencil, Plus, Trash2 } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import PolicyDialog from './parts/PolicyDialog.vue'
import { POLICY_KINDS, describeParams } from './parts/policyKinds'
import { adminApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { formatDate } from '@/utils/format'

const toast = useToast()
const { deptCode } = useReference()
const { data, loading, error, reload } = useAsync(() => adminApi.policies())
const groups = computed(() => Object.keys(POLICY_KINDS).map((k) => ({ kind: k, ...POLICY_KINDS[k], items: (data.value || []).filter((p) => p.kind === k) })).filter((g) => g.items.length))
const scopeLabel = (p) => (p.scope === 'college' ? 'Whole college' : p.scope === 'department' ? `Dept ${deptCode(p.scopeValue)}` : `Batch ${p.scopeValue}`)

const dialogOpen = ref(false)
const editing = ref(null)
const confirm = ref({ open: false })
function toggle(p) {
  confirm.value = { open: true, title: p.enabled ? 'Disable policy?' : 'Enable policy?', label: p.enabled ? 'Disable' : 'Enable', tone: p.enabled ? 'warning' : 'primary',
    text: `“${p.name}” ${p.enabled ? 'stops applying' : 'applies'} from the next eligibility check or offer.`,
    run: async () => {
      await adminApi.updatePolicy(p.id, { name: p.name, description: p.description, kind: p.kind, scope: p.scope, scopeValue: p.scopeValue || null, params: p.params, enabled: !p.enabled })
      toast.success('Policy updated'); reload()
    } }
}
function remove(p) {
  confirm.value = { open: true, title: 'Delete policy?', label: 'Delete', tone: 'danger', reason: true, text: `“${p.name}” is removed permanently. The deletion and your reason are kept in the audit log.`,
    run: async (reason) => { await adminApi.deletePolicy(p.id, reason); toast.success('Policy deleted'); reload() } }
}
</script>

<template>
  <PageHeader title="Placement policies" subtitle="College rules applied to eligibility checks and offers.">
    <template #actions><button class="btn btn-primary" @click="editing = null; dialogOpen = true"><Plus class="size-4" /> Add policy</button></template>
  </PageHeader>
  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" @retry="reload">
    <div v-if="!groups.length" class="card"><EmptyState :icon="Gavel" title="No policies configured" message="Add a policy to enforce offer limits, tier rules and more." /></div>
    <div class="space-y-6">
      <SectionCard v-for="g in groups" :key="g.kind" :title="g.label" :subtitle="g.help">
        <ul class="divide-y divide-line">
          <li v-for="p in g.items" :key="p.id" class="flex flex-wrap items-start gap-3 py-3">
            <div class="min-w-0 flex-1">
              <p class="flex flex-wrap items-center gap-2 font-medium">{{ p.name }}<StatusChip tone="info" :label="scopeLabel(p)" />
                <StatusChip :tone="p.enabled ? 'success' : 'neutral'" :label="p.enabled ? 'Enabled' : 'Disabled'" /></p>
              <p v-if="p.description" class="text-sm text-slate-700">{{ p.description }}</p>
              <p class="mt-1 font-mono text-xs text-muted">{{ describeParams(p.kind, p.params) }}</p>
              <p class="text-xs text-muted">Updated {{ formatDate(p.updatedAt) }} by {{ p.updatedBy }}</p>
            </div>
            <button role="switch" :aria-checked="p.enabled" :aria-label="`${p.enabled ? 'Disable' : 'Enable'} ${p.name}`" class="relative mt-1 h-6 w-11 rounded-full transition"
              :class="p.enabled ? 'bg-brand-600' : 'bg-slate-300'" @click="toggle(p)">
              <span class="absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition" :class="p.enabled && 'translate-x-5'" />
            </button>
            <button class="btn-icon" aria-label="Edit policy" @click="editing = p; dialogOpen = true"><Pencil class="size-4" /></button>
            <button class="btn-icon hover:text-red-700" aria-label="Delete policy" @click="remove(p)"><Trash2 class="size-4" /></button>
          </li>
        </ul>
      </SectionCard>
    </div>
  </AsyncBlock>
  <PolicyDialog v-model:open="dialogOpen" :policy="editing" @saved="toast.success('Policy saved'); reload()" />
  <ConfirmDialog v-model:open="confirm.open" :title="confirm.title || ''" :confirm-label="confirm.label" :tone="confirm.tone"
    :require-reason="confirm.reason" reason-label="Reason for deleting" :action="confirm.run">{{ confirm.text }}</ConfirmDialog>
</template>
