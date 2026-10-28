<script setup>
import { ref } from 'vue'
import AuthFrame from './AuthFrame.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { authApi } from '@/api'

const email = ref('')
const error = ref('')
const failure = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  error.value = /^\S+@\S+\.\S+$/.test(email.value.trim()) ? '' : 'Enter a valid e-mail address'
  if (error.value) return
  busy.value = true
  failure.value = ''
  try {
    message.value = (await authApi.forgotPassword(email.value.trim())).message
  } catch (e) {
    failure.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthFrame title="Reset your password" subtitle="We'll send a reset link to your college e-mail.">
    <div v-if="message" class="space-y-4">
      <p class="alert alert-success">{{ message }}</p>
      <RouterLink to="/login" class="btn btn-secondary w-full">Back to sign in</RouterLink>
    </div>
    <form v-else class="space-y-4" novalidate @submit.prevent="submit">
      <p v-if="failure" class="alert alert-error">{{ failure }}</p>
      <FormField label="College e-mail" :error="error" for="email">
        <input id="email" v-model="email" type="email" class="input" :class="error && 'input-error'" autocomplete="email" autofocus />
      </FormField>
      <button type="submit" class="btn btn-primary w-full py-2.5" :disabled="busy"><Spinner v-if="busy" /> Send reset link</button>
      <RouterLink to="/login" class="link block text-center text-sm">Back to sign in</RouterLink>
    </form>
  </AuthFrame>
</template>
