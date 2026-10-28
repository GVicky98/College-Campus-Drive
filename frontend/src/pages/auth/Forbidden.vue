<script setup>
import { Lock } from '@lucide/vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
defineProps({ embedded: Boolean })
const auth = useAuthStore()
const router = useRouter()
</script>

<template>
  <div class="flex flex-col items-center justify-center px-6 text-center" :class="embedded ? 'py-20' : 'min-h-screen'">
    <div class="mb-4 flex size-14 items-center justify-center rounded-full bg-red-50 text-red-700"><Lock class="size-7" /></div>
    <h1 class="text-xl">Access denied</h1>
    <p class="mt-2 max-w-md text-muted">
      {{ embedded ? 'Your role does not include the permission needed for this page.' : 'This area is not available for your account.' }}
    </p>
    <div class="mt-6 flex gap-2">
      <button class="btn btn-secondary" @click="router.back()">Go back</button>
      <RouterLink :to="auth.isSignedIn ? auth.home : '/login'" class="btn btn-primary">
        {{ auth.isSignedIn ? 'Go to my dashboard' : 'Go to sign in' }}
      </RouterLink>
    </div>
  </div>
</template>
