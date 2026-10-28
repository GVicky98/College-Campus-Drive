<script setup>
import { ref } from 'vue'
import { CircleCheck, CircleX, Gift } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import CompanyLogo from '@/components/CompanyLogo.vue'
import { offersApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useToast } from '@/composables/toast'
import { daysUntil, formatDate, formatPackage } from '@/utils/format'

const toast = useToast()
const { data, loading, error, reload } = useAsync(() => Promise.all([offersApi.mine(), offersApi.policies()]))
const pending = ref(null) // { view, decision }
const open = ref(false)

function ask(view, decision) { pending.value = { view, decision }; open.value = true }
async function respond() {
  await offersApi.respond(pending.value.view.offer.id, pending.value.decision)
  toast.success(pending.value.decision === 'accepted' ? 'Offer accepted — congratulations!' : 'Offer declined')
  reload()
}
</script>

<template>
  <PageHeader title="My Offers" subtitle="Offers issued to you by the placement cell." />
  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" @retry="reload">
    <template v-if="data">
      <div class="grid gap-6 lg:grid-cols-3">
        <div class="space-y-4 lg:col-span-2">
          <p class="alert alert-info">Offer details are set by the placement cell. You can accept or decline an offer before its deadline.</p>
          <div v-if="!data[0].length" class="card"><EmptyState :icon="Gift" title="No offers yet" message="When you are selected and an offer is issued, it appears here." /></div>
          <article v-for="v in data[0]" :key="v.offer.id" class="card p-5">
            <div class="flex flex-wrap items-start gap-3">
              <CompanyLogo :company="v.company" />
              <div class="min-w-0 flex-1">
                <p class="font-semibold">{{ v.job.title }}</p>
                <p class="text-sm text-muted">{{ v.company.name }}</p>
              </div>
              <StatusChip kind="offer" :value="v.offer.status" />
            </div>
            <dl class="mt-4 grid gap-4 text-sm sm:grid-cols-3">
              <div><dt class="text-xs text-muted">Compensation</dt><dd class="font-semibold">{{ formatPackage(v.offer.ctcLpa) }}</dd></div>
              <div><dt class="text-xs text-muted">Offer date</dt><dd>{{ formatDate(v.offer.offeredAt) }}</dd></div>
              <div><dt class="text-xs text-muted">Accept by</dt>
                <dd>{{ formatDate(v.offer.acceptBy) }}
                  <span v-if="v.offer.status === 'received'" class="text-xs" :class="daysUntil(v.offer.acceptBy) <= 3 ? 'text-red-700' : 'text-muted'">
                    · {{ daysUntil(v.offer.acceptBy) > 0 ? `${daysUntil(v.offer.acceptBy)}d left` : 'expired' }}</span>
                </dd></div>
            </dl>
            <div v-if="v.offer.policyChecks.length" class="mt-4">
              <p class="text-xs font-medium text-muted">Policy checks at issue</p>
              <ul class="mt-1 space-y-1">
                <li v-for="c in v.offer.policyChecks" :key="c.label" class="flex items-center gap-1.5 text-sm">
                  <component :is="c.passed ? CircleCheck : CircleX" class="size-4" :class="c.passed ? 'text-green-600' : 'text-red-600'" />
                  {{ c.label }} <span class="text-muted">— {{ c.detail }}</span>
                </li>
              </ul>
            </div>
            <div v-if="v.offer.status === 'received'" class="mt-4 flex gap-2">
              <button class="btn btn-primary" :disabled="daysUntil(v.offer.acceptBy) <= 0" @click="ask(v, 'accepted')">Accept offer</button>
              <button class="btn btn-secondary" :disabled="daysUntil(v.offer.acceptBy) <= 0" @click="ask(v, 'declined')">Decline</button>
            </div>
          </article>
        </div>
        <SectionCard title="Placement policies">
          <p v-if="!data[1].length" class="text-sm text-muted">No policies are active.</p>
          <ul v-else class="space-y-3">
            <li v-for="p in data[1]" :key="p.id" class="text-sm"><p class="font-medium">{{ p.name }}</p><p class="text-xs text-muted">{{ p.description }}</p></li>
          </ul>
        </SectionCard>
      </div>
      <ConfirmDialog v-if="pending" v-model:open="open" :title="pending.decision === 'accepted' ? 'Accept this offer?' : 'Decline this offer?'"
        :confirm-label="pending.decision === 'accepted' ? 'Accept offer' : 'Decline offer'" :tone="pending.decision === 'accepted' ? 'primary' : 'danger'" :action="respond">
        <p><b>{{ pending.view.company.name }} — {{ pending.view.job.title }}</b> at {{ formatPackage(pending.view.offer.ctcLpa) }}.</p>
        <p class="mt-2 text-muted">This cannot be undone from your side. Accepting may limit future drives under the placement policies.</p>
      </ConfirmDialog>
    </template>
  </AsyncBlock>
</template>
