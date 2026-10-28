<script setup>
import { CheckCircle2, GraduationCap } from '@lucide/vue'
import { usePublicSettings } from '@/composables/usePublicSettings'
defineProps({ title: String, subtitle: String })
const { settings } = usePublicSettings()
const points = ['Track every job, application and offer in one place', 'Eligibility checked automatically against college rules', 'An AI assistant that answers from your real records']
</script>

<template>
  <div class="grid min-h-screen lg:grid-cols-2">
    <aside class="relative hidden flex-col justify-between bg-navy-800 p-12 text-white lg:flex">
      <div class="flex items-center gap-3">
        <div class="flex size-10 items-center justify-center rounded-xl bg-white/10"><GraduationCap class="size-6" /></div>
        <span class="text-lg font-semibold">Campus Assistant</span>
      </div>
      <div>
        <h2 class="text-4xl leading-tight font-semibold">Placements,<br />organised.</h2>
        <ul class="mt-8 space-y-4 text-white/80">
          <li v-for="p in points" :key="p" class="flex gap-3"><CheckCircle2 class="mt-0.5 size-5 shrink-0 text-blue-300" />{{ p }}</li>
        </ul>
      </div>
      <p class="text-sm text-white/50">{{ settings.collegeName }} · Placement Cell</p>
    </aside>
    <main class="flex items-center justify-center px-4 py-12 sm:px-8">
      <div class="w-full max-w-md">
        <div class="mb-8 flex items-center gap-3 lg:hidden">
          <div class="flex size-10 items-center justify-center rounded-xl bg-navy-800 text-white"><GraduationCap class="size-6" /></div>
          <span class="text-lg font-semibold">Campus Assistant</span>
        </div>
        <h1 class="text-2xl">{{ title }}</h1>
        <p v-if="subtitle" class="mt-1 text-muted">{{ subtitle }}</p>
        <div class="mt-8"><slot /></div>
      </div>
    </main>
  </div>
</template>
