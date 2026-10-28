<script setup>
import { SearchX } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
</script>

<template>
  <div class="flex flex-col items-center justify-center px-6 py-24 text-center">
    <div class="mb-4 flex size-14 items-center justify-center rounded-full bg-slate-100 text-slate-600"><SearchX class="size-7" /></div>
    <h1 class="text-xl">Page not found</h1>
    <p class="mt-2 text-muted">The page you are looking for does not exist or has moved.</p>
    <RouterLink :to="auth.isSignedIn ? auth.home : '/login'" class="btn btn-primary mt-6">
      {{ auth.isSignedIn ? 'Back to dashboard' : 'Back to sign in' }}
    </RouterLink>
  </div>
</template>
