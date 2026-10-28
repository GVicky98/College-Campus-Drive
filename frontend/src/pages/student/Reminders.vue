<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { BellRing, Pencil, Plus, Trash2 } from '@lucide/vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import Tabs from '@/components/ui/Tabs.vue'
import SelectFilter from '@/components/ui/SelectFilter.vue'
import AsyncBlock from '@/components/ui/AsyncBlock.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusChip from '@/components/ui/StatusChip.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ReminderDialog from '@/components/ReminderDialog.vue'
import NotificationsList from '@/components/NotificationsList.vue'
import NotificationPrefs from '@/components/NotificationPrefs.vue'
import { remindersApi } from '@/api'
import { useAsync } from '@/composables/useAsync'
import { useToast } from '@/composables/toast'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const toast = useToast()
const tab = ref(route.query.tab || 'reminders')
const kind = ref('')
const { data, loading, error, reload } = useAsync(() => remindersApi.list())
const rows = computed(() => (data.value || []).filter((r) => !kind.value || r.reminder.kind === kind.value))
const upcoming = computed(() => rows.value.filter((r) => !r.reminder.done))
const completed = computed(() => rows.value.filter((r) => r.reminder.done))

const dialogOpen = ref(false)
const editing = ref(null)
const deleting = ref(null)
const deleteOpen = ref(false)

function edit(r) { editing.value = r; dialogOpen.value = true }
function create() { editing.value = null; dialogOpen.value = true }
async function toggle(r) {
  try { Object.assign(r, await remindersApi.toggle(r.reminder.id)) } catch (e) { toast.error(e.message) }
}
async function remove() {
  await remindersApi.remove(deleting.value.reminder.id)
  toast.success('Reminder deleted')
  reload()
}
const KINDS = [{ value: 'drive', label: 'Placement drive' }, { value: 'deadline', label: 'Application deadline' }, { value: 'interview', label: 'Interview' }, { value: 'custom', label: 'Personal' }]
</script>

<template>
  <PageHeader title="Reminders & Notifications" subtitle="Your personal reminders and updates from the placement cell." />
  <Tabs v-model="tab" :tabs="[{ value: 'reminders', label: 'Reminders' }, { value: 'notifications', label: 'Notifications' }, { value: 'prefs', label: 'Preferences' }]" />

  <template v-if="tab === 'reminders'">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <SelectFilter v-model="kind" label="Type" :options="KINDS" />
      <button class="btn btn-primary ml-auto" @click="create"><Plus class="size-4" /> New reminder</button>
    </div>
    <AsyncBlock :loading="loading" :error="error" :has-data="!!data" @retry="reload">
      <div class="grid gap-6 lg:grid-cols-2">
        <SectionCard v-for="group in [{ title: `Upcoming (${upcoming.length})`, list: upcoming }, { title: `Completed (${completed.length})`, list: completed }]"
          :key="group.title" :title="group.title" :padded="false">
          <EmptyState v-if="!group.list.length" :icon="BellRing" title="Nothing here" />
          <ul v-else class="divide-y divide-line">
            <li v-for="r in group.list" :key="r.reminder.id" class="flex items-start gap-3 px-5 py-3">
              <input type="checkbox" class="checkbox mt-1" :checked="r.reminder.done" :aria-label="`Mark ${r.reminder.title} done`" @change="toggle(r)" />
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium" :class="r.reminder.done && 'text-muted line-through'">{{ r.reminder.title }}</p>
                <p class="text-xs text-muted">{{ formatDateTime(r.reminder.at) }}<span v-if="r.jobTitle"> · {{ r.companyName }} — {{ r.jobTitle }}</span></p>
                <StatusChip class="mt-1" kind="reminder" :value="r.reminder.kind" />
              </div>
              <button class="btn-icon" aria-label="Edit reminder" @click="edit(r)"><Pencil class="size-4" /></button>
              <button class="btn-icon hover:text-red-700" aria-label="Delete reminder" @click="deleting = r; deleteOpen = true"><Trash2 class="size-4" /></button>
            </li>
          </ul>
        </SectionCard>
      </div>
    </AsyncBlock>
  </template>
  <NotificationsList v-else-if="tab === 'notifications'" />
  <SectionCard v-else title="Notification preferences"><NotificationPrefs /></SectionCard>

  <ReminderDialog v-model:open="dialogOpen" :reminder="editing" @saved="reload(); toast.success('Reminder saved')" />
  <ConfirmDialog v-model:open="deleteOpen" title="Delete reminder?" confirm-label="Delete" tone="danger" :action="remove">
    “{{ deleting?.reminder.title }}” will be removed.
  </ConfirmDialog>
</template>
