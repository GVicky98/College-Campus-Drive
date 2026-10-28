<script setup>
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AuthFrame from './AuthFrame.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { authApi } from '@/api'
import { passwordProblem } from '@/utils/validation'

const token = useRoute().query.token
const form = reactive({ password: '', confirm: '' })
const errors = reactive({})
const failure = ref('')
const done = ref(false)
const busy = ref(false)

async function submit() {
  errors.password = passwordProblem(form.password)
  errors.confirm = form.confirm === form.password ? '' : 'The passwords do not match'
  if (errors.password || errors.confirm) return
  busy.value = true
  failure.value = ''
  try {
    await authApi.resetPassword(token, form.password)
    done.value = true
  } catch (e) {
    failure.value = e.details?.password?.join(' ') || e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthFrame title="Choose a new password" subtitle="8+ characters with an upper-case letter and a digit.">
    <div v-if="!token" class="space-y-4">
      <p class="alert alert-error">This reset link is invalid.</p>
      <RouterLink to="/forgot-password" class="btn btn-secondary w-full">Request a new link</RouterLink>
    </div>
    <div v-else-if="done" class="space-y-4">
      <p class="alert alert-success">Password updated. You can sign in now.</p>
      <RouterLink to="/login" class="btn btn-primary w-full">Go to sign in</RouterLink>
    </div>
    <form v-else class="space-y-4" novalidate @submit.prevent="submit">
      <p v-if="failure" class="alert alert-error">{{ failure }}</p>
      <FormField label="New password" :error="errors.password" for="pw">
        <input id="pw" v-model="form.password" type="password" class="input" autocomplete="new-password" />
      </FormField>
      <FormField label="Confirm password" :error="errors.confirm" for="pw2">
        <input id="pw2" v-model="form.confirm" type="password" class="input" autocomplete="new-password" />
      </FormField>
      <button type="submit" class="btn btn-primary w-full py-2.5" :disabled="busy"><Spinner v-if="busy" /> Update password</button>
    </form>
  </AuthFrame>
</template>
