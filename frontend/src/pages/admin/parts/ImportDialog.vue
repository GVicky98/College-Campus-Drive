<script setup>
import { ref, watch } from 'vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { usersApi } from '@/api'
import { parseCsv } from '@/utils/csv'
import { downloadText, toCsv } from '@/utils/format'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['update:open', 'imported'])
const COLUMNS = ['studentCode', 'name', 'email', 'departmentCode', 'graduationYear', 'cgpa']
const text = ref('')
const error = ref('')
const busy = ref(false)
const result = ref(null)

watch(() => props.open, (v) => { if (v) { text.value = ''; error.value = ''; result.value = null } })

function template() {
  downloadText('student-import-template.csv', toCsv(COLUMNS, [['23CSE150', 'Priya Sharma', 'priya.sharma@college.edu', 'CSE', '2027', '8.25']]))
}
async function pick(e) {
  const file = e.target.files[0]
  error.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.csv')) { error.value = 'Choose a .csv file'; return }
  if (file.size > 1024 * 1024) { error.value = 'The file must be 1 MB or smaller'; return }
  text.value = await file.text()
}
async function submit() {
  let rows = parseCsv(text.value)
  const hasHeader = rows.length && rows[0][0]?.trim().toLowerCase() === 'studentcode' // the header is optional
  if (hasHeader) rows = rows.slice(1)
  if (!rows.length) { error.value = 'Paste rows or choose a file'; return }
  if (rows.length > 500) { error.value = `At most 500 rows at a time (you have ${rows.length})`; return }
  busy.value = true
  error.value = ''
  try {
    const r = await usersApi.importStudents(rows.map((row) => Object.fromEntries(COLUMNS.map((c, i) => [c, (row[i] ?? '').trim()]))))
    // The server numbers rows as file lines with a header on line 1; match what the user actually gave.
    if (!hasHeader) r.errors.forEach((e) => { e.row -= 1 })
    result.value = r
    if (result.value.imported) emit('imported', result.value)
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
function errorReport() {
  downloadText('import-errors.csv', toCsv(['Row', 'Field', 'Problem', 'Value'], result.value.errors.map((e) => [e.row, e.field, e.message, e.value])))
}
</script>

<template>
  <BaseDialog :open="open" title="Import students" size="lg" :persistent="busy" @update:open="emit('update:open', $event)">
    <div v-if="result" class="space-y-4">
      <p class="alert" :class="result.errors.length ? 'alert-warning' : 'alert-success'">Imported {{ result.imported }} of {{ result.total }} rows. New students are invited and choose their password from a one-time link.</p>
      <div v-if="result.errors.length" class="max-h-72 overflow-auto rounded-xl border border-line">
        <table class="table"><thead><tr><th>Row</th><th>Field</th><th>Problem</th><th>Value</th></tr></thead>
          <tbody><tr v-for="(e, i) in result.errors" :key="i"><td>{{ e.row }}</td><td>{{ e.field }}</td><td>{{ e.message }}</td><td class="text-muted">{{ e.value }}</td></tr></tbody></table>
      </div>
    </div>
    <div v-else class="space-y-4">
      <p class="text-sm text-muted">Columns, in order: <code class="rounded bg-slate-100 px-1 text-xs">{{ COLUMNS.join(',') }}</code>. The header row is optional; CGPA may be empty. Up to 500 rows.</p>
      <button class="btn btn-secondary btn-sm" @click="template">Download template</button>
      <p v-if="error" class="alert alert-error">{{ error }}</p>
      <FormField label="CSV file" for="imp-file"><input id="imp-file" type="file" accept=".csv" class="input" @change="pick" /></FormField>
      <FormField label="…or paste rows" for="imp-text"><textarea id="imp-text" v-model="text" rows="7" class="input font-mono text-xs" placeholder="23CSE150,Priya Sharma,priya@college.edu,CSE,2027,8.25" /></FormField>
    </div>
    <template #footer>
      <template v-if="result">
        <button v-if="result.errors.length" class="btn btn-secondary" @click="errorReport">Download error report</button>
        <button class="btn btn-secondary" @click="result = null; text = ''">Import another file</button>
        <button class="btn btn-primary" @click="emit('update:open', false)">Done</button>
      </template>
      <template v-else>
        <button class="btn btn-secondary" :disabled="busy" @click="emit('update:open', false)">Cancel</button>
        <button class="btn btn-primary" :disabled="busy" @click="submit"><Spinner v-if="busy" /> Import</button>
      </template>
    </template>
  </BaseDialog>
</template>
