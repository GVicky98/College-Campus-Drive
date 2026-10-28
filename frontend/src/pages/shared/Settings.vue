<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import Tabs from '@/components/ui/Tabs.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import NotificationPrefs from '@/components/NotificationPrefs.vue'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useReference } from '@/composables/useReference'
import { useToast } from '@/composables/toast'
import { ROLE_LABEL, formatDateTime } from '@/utils/format'
import { passwordProblem } from '@/utils/validation'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()
const { deptName } = useReference()
const tab = ref('account')
const pw = reactive({ current: '', next: '', confirm: '' })
const errors = reactive({})
const busy = ref(false)
const failure = ref('')

const device = computed(() => {
  const ua = navigator.userAgent
  const browser = /Edg\//.test(ua) ? 'Edge' : /Chrome\//.test(ua) ? 'Chrome' : /Firefox\//.test(ua) ? 'Firefox' : /Safari\//.test(ua) ? 'Safari' : 'Browser'
  const os = /Windows/.test(ua) ? 'Windows' : /Mac OS/.test(ua) ? 'macOS' : /Android/.test(ua) ? 'Android' : /iPhone|iPad/.test(ua) ? 'iOS' : /Linux/.test(ua) ? 'Linux' : ''
  return [browser, os].filter(Boolean).join(' on ')
})

async function changePassword() {
  errors.current = pw.current ? '' : 'Enter your current password'
  errors.next = passwordProblem(pw.next)
  errors.confirm = pw.confirm === pw.next ? '' : 'The passwords do not match'
  if (Object.values(errors).some(Boolean)) return
  busy.value = true
  failure.value = ''
  try {
    await authApi.changePassword({ currentPassword: pw.current, newPassword: pw.next })
    Object.assign(pw, { current: '', next: '', confirm: '' })
    toast.success('Password changed')
  } catch (e) {
    failure.value = e.details?.password?.join(' ') || e.message
  } finally { busy.value = false }
}
async function logout() { await auth.logout(); router.replace('/login') }
</script>

<template>
  <PageHeader title="Settings" subtitle="Your account, security and notifications." />
  <Tabs v-model="tab" :tabs="[{ value: 'account', label: 'Account' }, { value: 'security', label: 'Security & sessions' }, { value: 'notifications', label: 'Notifications' }]" />

  <SectionCard v-if="tab === 'account'" title="Account" subtitle="Managed by the placement cell. Ask an administrator to change these.">
    <dl class="grid gap-4 text-sm sm:grid-cols-2">
      <div><dt class="text-xs text-muted">Name</dt><dd class="font-medium">{{ auth.user.name }}</dd></div>
      <div><dt class="text-xs text-muted">E-mail</dt><dd class="font-medium">{{ auth.user.email }}</dd></div>
      <div><dt class="text-xs text-muted">User ID</dt><dd class="font-medium">{{ auth.user.userCode }}</dd></div>
      <div><dt class="text-xs text-muted">Role</dt><dd class="font-medium">{{ ROLE_LABEL[auth.role] }}</dd></div>
      <div><dt class="text-xs text-muted">Department</dt><dd class="font-medium">{{ auth.user.departmentId ? deptName(auth.user.departmentId) : '—' }}</dd></div>
      <div><dt class="text-xs text-muted">Status</dt><dd><StatusChip kind="user" :value="auth.user.status" /></dd></div>
    </dl>
  </SectionCard>

  <div v-else-if="tab === 'security'" class="grid gap-6 lg:grid-cols-2">
    <SectionCard title="Change password">
      <form class="space-y-4" novalidate @submit.prevent="changePassword">
        <p v-if="failure" class="alert alert-error">{{ failure }}</p>
        <FormField label="Current password" :error="errors.current" for="pw0"><input id="pw0" v-model="pw.current" type="password" class="input" autocomplete="current-password" /></FormField>
        <FormField label="New password" :error="errors.next" hint="8+ characters, an upper-case letter and a digit" for="pw1"><input id="pw1" v-model="pw.next" type="password" class="input" autocomplete="new-password" /></FormField>
        <FormField label="Confirm new password" :error="errors.confirm" for="pw2"><input id="pw2" v-model="pw.confirm" type="password" class="input" autocomplete="new-password" /></FormField>
        <button type="submit" class="btn btn-primary" :disabled="busy"><Spinner v-if="busy" /> Change password</button>
      </form>
    </SectionCard>
    <SectionCard title="This session">
      <dl class="space-y-3 text-sm">
        <div class="flex justify-between gap-3"><dt class="text-muted">Signed in as</dt><dd>{{ auth.user.email }}</dd></div>
        <div class="flex justify-between gap-3"><dt class="text-muted">Last sign-in</dt><dd>{{ formatDateTime(auth.user.lastLoginAt) }}</dd></div>
        <div class="flex justify-between gap-3"><dt class="text-muted">This device</dt><dd>{{ device }}</dd></div>
        <div class="flex justify-between gap-3"><dt class="text-muted">Session</dt><dd>Kept by a secure cookie; changing your password signs out other devices.</dd></div>
      </dl>
      <button class="btn btn-secondary mt-5" @click="logout">Log out of this device</button>
    </SectionCard>
  </div>

  <SectionCard v-else title="Notification preferences"><NotificationPrefs instant /></SectionCard>
</template>
