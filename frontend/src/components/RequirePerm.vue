<script setup>
// Renders the page only if the user holds ANY of the route's `meta.perm` permissions.
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Forbidden from '@/pages/auth/Forbidden.vue'

const route = useRoute()
const auth = useAuthStore()
const allowed = computed(() => {
  const perm = route.matched.at(-1)?.meta.perm
  return !perm || auth.can(perm)
})
</script>

<template>
  <slot v-if="allowed" />
  <Forbidden v-else embedded />
</template>
