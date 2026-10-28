<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff } from '@lucide/vue'
import AuthFrame from './AuthFrame.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ identifier: '', password: '', remember: false })
const errors = reactive({})
const show = ref(false)
const busy = ref(false)
const failure = ref('')

async function submit() {
  errors.identifier = form.identifier.trim() ? '' : 'Enter your college e-mail or user ID'
  errors.password = form.password ? '' : 'Enter your password'
  if (errors.identifier || errors.password) return
  busy.value = true
  failure.value = ''
  try {
    await auth.login(form.identifier.trim(), form.password, form.remember)
    const from = route.query.from
    router.replace(typeof from === 'string' && from.startsWith(`/${auth.role}`) ? from : auth.home)
  } catch (e) {
    failure.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthFrame title="Sign in" subtitle="Use your college account to continue.">
    <form class="space-y-4" novalidate @submit.prevent="submit">
      <p v-if="failure" class="alert alert-error" role="alert">{{ failure }}</p>
      <FormField label="College e-mail or user ID" :error="errors.identifier" for="identifier">
        <input id="identifier" v-model="form.identifier" class="input" :class="errors.identifier && 'input-error'" autocomplete="username" autofocus />
      </FormField>
      <FormField label="Password" :error="errors.password" for="password">
        <div class="relative">
          <input id="password" v-model="form.password" :type="show ? 'text' : 'password'" class="input pr-10"
            :class="errors.password && 'input-error'" autocomplete="current-password" />
          <button type="button" class="absolute top-1/2 right-2 -translate-y-1/2 text-slate-400 hover:text-ink"
            :aria-label="show ? 'Hide password' : 'Show password'" @click="show = !show">
            <component :is="show ? EyeOff : Eye" class="size-4" />
          </button>
        </div>
      </FormField>
      <div class="flex items-center justify-between">
        <label class="flex items-center gap-2 text-sm"><input v-model="form.remember" type="checkbox" class="checkbox" /> Remember me</label>
        <RouterLink to="/forgot-password" class="link text-sm">Forgot password?</RouterLink>
      </div>
      <button type="submit" class="btn btn-primary w-full py-2.5" :disabled="busy">
        <Spinner v-if="busy" /> {{ busy ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </AuthFrame>
</template>
