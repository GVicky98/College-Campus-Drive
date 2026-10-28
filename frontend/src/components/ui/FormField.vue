<script setup>
defineProps({ label: String, error: String, hint: String, for: String, required: Boolean })
</script>

<template>
  <div>
    <label v-if="label" class="label" :for="$props.for">{{ label }}<span v-if="required" class="text-red-600"> *</span></label>
    <slot />
    <p v-if="error" class="field-error">{{ error }}</p>
    <p v-else-if="hint" class="hint">{{ hint }}</p>
  </div>
</template>
