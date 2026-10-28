<script setup>
import { computed, ref } from 'vue'
import { GraduationCap, ShieldCheck, Users } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { adminApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/toast'

const auth = useAuthStore()
const toast = useToast()
const { data, loading, error, reload } = useAsync(() => adminApi.roles())
const groups = computed(() => {
  const out = {}
  for (const p of data.value?.permissions || []) (out[p.module] ||= []).push(p)
  return out
})
// The server refuses these too; the switches are simply locked here.
const locked = (role, key) => (role === 'admin' && ['roles.manage', 'users.manage'].includes(key)) || (role !== 'admin' && key === 'roles.manage')
const pending = ref({ open: false })
function ask(role, p, enabled) {
  pending.value = { open: true, role, p, enabled }
}
async function apply() {
  const { role, p, enabled } = pending.value
  data.value.matrix[role] = await adminApi.setPermission(role, p.key, enabled)
  toast.success(`${enabled ? 'Granted' : 'Revoked'} “${p.label}” for ${role}`)
  if (role === auth.role) auth.reloadMe()
}
</script>

<template>
  <PageHeader title="Roles & permissions" subtitle="What each role may do. Changes apply on the user's next request." />
  <AsyncBlock :loading="loading" :error="error" :has-data="!!data" :rows="10" @retry="reload">
    <template v-if="data">
      <div class="mb-6 grid gap-4 sm:grid-cols-3">
        <MetricCard label="Administrators" :value="data.userCounts.admin" :icon="ShieldCheck" tone="purple" />
        <MetricCard label="Faculty" :value="data.userCounts.faculty" :icon="Users" />
        <MetricCard label="Students" :value="data.userCounts.student" :icon="GraduationCap" tone="green" />
      </div>
      <div class="card overflow-x-auto">
        <table class="table">
          <thead><tr><th>Permission</th><th class="text-center">Admin</th><th class="text-center">Faculty</th><th class="text-center">Student</th></tr></thead>
          <tbody>
            <template v-for="(perms, module) in groups" :key="module">
              <tr><td colspan="4" class="bg-slate-50 text-xs font-semibold tracking-wide text-muted uppercase">{{ module }}</td></tr>
              <tr v-for="p in perms" :key="p.key">
                <td><p class="font-medium">{{ p.label }}</p><p class="text-xs text-muted">{{ p.description }} · <code>{{ p.key }}</code></p></td>
                <td v-for="role in ['admin', 'faculty']" :key="role" class="text-center">
                  <button role="switch" :aria-checked="data.matrix[role].includes(p.key)" :aria-label="`${p.label} for ${role}`"
                    :disabled="locked(role, p.key) || auth.role !== 'admin'" class="relative h-6 w-11 rounded-full transition disabled:opacity-50"
                    :class="data.matrix[role].includes(p.key) ? 'bg-brand-600' : 'bg-slate-300'" @click="ask(role, p, !data.matrix[role].includes(p.key))">
                    <span class="absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition" :class="data.matrix[role].includes(p.key) && 'translate-x-5'" />
                  </button>
                </td>
                <td class="text-center text-xs text-muted">Own records only</td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <ConfirmDialog v-model:open="pending.open" :title="pending.enabled ? 'Grant permission?' : 'Revoke permission?'"
        :confirm-label="pending.enabled ? 'Grant' : 'Revoke'" :tone="pending.enabled ? 'primary' : 'warning'" :action="apply">
        <p>{{ pending.enabled ? 'Give' : 'Remove' }} <b>{{ pending.p?.label }}</b> {{ pending.enabled ? 'to' : 'from' }} every <b>{{ pending.role }}</b> account.</p>
      </ConfirmDialog>
    </template>
  </AsyncBlock>
</template>
