<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import Tabs from '@/components/ui/Tabs.vue'
import Companies from '@/pages/faculty/Companies.vue'
import Jobs from '@/pages/faculty/Jobs.vue'

const route = useRoute()
const router = useRouter()
const tab = computed({ get: () => (route.path.endsWith('/jobs') ? 'jobs' : 'companies'), set: (v) => router.replace(`/admin/${v}`) })
</script>

<template>
  <PageHeader title="Companies & jobs" subtitle="Recruiters and the jobs they offer." />
  <Tabs v-model="tab" :tabs="[{ value: 'companies', label: 'Companies' }, { value: 'jobs', label: 'Jobs' }]" />
  <Companies v-if="tab === 'companies'" embedded />
  <Jobs v-else embedded />
</template>
