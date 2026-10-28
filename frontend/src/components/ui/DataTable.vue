<script setup>
// Table with loading / error / empty states, optional server pagination and row selection.
// Custom cells: <template #cell-name="{ row }">...</template>
import { computed } from 'vue'
import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import Pagination from './Pagination.vue'

const props = defineProps({
  columns: { type: Array, required: true }, // [{ key, label, class?, hide?: 'sm'|'md'|'lg', align?: 'right' }]
  rows: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  loading: Boolean,
  error: Object,
  total: Number,
  page: Number,
  pageSize: Number,
  selectable: Boolean,
  selected: { type: Array, default: () => [] },
  clickable: Boolean,
  emptyTitle: { type: String, default: 'No records found' },
  emptyMessage: String,
})
const emit = defineEmits(['row-click', 'page', 'update:selected', 'retry'])

const keyOf = (row) => (typeof props.rowKey === 'function' ? props.rowKey(row) : row[props.rowKey])
const hideClass = { sm: 'hidden sm:table-cell', md: 'hidden md:table-cell', lg: 'hidden lg:table-cell' }
const pageKeys = computed(() => props.rows.map(keyOf))
const allSelected = computed(() => pageKeys.value.length > 0 && pageKeys.value.every((k) => props.selected.includes(k)))
const someSelected = computed(() => !allSelected.value && pageKeys.value.some((k) => props.selected.includes(k)))

function toggleAll() {
  const set = new Set(props.selected)
  if (allSelected.value) pageKeys.value.forEach((k) => set.delete(k))
  else pageKeys.value.forEach((k) => set.add(k))
  emit('update:selected', [...set])
}
function toggle(row) {
  const k = keyOf(row)
  emit('update:selected', props.selected.includes(k) ? props.selected.filter((x) => x !== k) : [...props.selected, k])
}
const value = (row, key) => key.split('.').reduce((o, p) => o?.[p], row)
</script>

<template>
  <div class="card overflow-hidden">
    <div v-if="$slots.toolbar" class="border-b border-line px-4 py-3"><slot name="toolbar" /></div>
    <ErrorState v-if="error && !rows.length" :error="error" @retry="emit('retry')" />
    <div v-else class="overflow-x-auto transition-opacity" :class="loading && rows.length && 'opacity-60'">
      <table class="table">
        <thead>
          <tr>
            <th v-if="selectable" class="w-10">
              <input type="checkbox" class="checkbox" :checked="allSelected" :indeterminate="someSelected"
                aria-label="Select all on this page" @change="toggleAll" />
            </th>
            <th v-for="c in columns" :key="c.key" :class="[hideClass[c.hide], c.align === 'right' && 'text-right', c.class]">{{ c.label }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading && !rows.length">
            <tr v-for="i in 5" :key="'s' + i">
              <td v-if="selectable" />
              <td v-for="c in columns" :key="c.key" :class="hideClass[c.hide]"><div class="skeleton h-4 w-3/4" /></td>
            </tr>
          </template>
          <tr v-for="row in rows" :key="keyOf(row)" :class="clickable && 'cursor-pointer hover:bg-slate-50'"
            @click="clickable && emit('row-click', row)">
            <td v-if="selectable" @click.stop>
              <input type="checkbox" class="checkbox" :checked="selected.includes(keyOf(row))" aria-label="Select row" @change="toggle(row)" />
            </td>
            <td v-for="c in columns" :key="c.key" :class="[hideClass[c.hide], c.align === 'right' && 'text-right', c.class]">
              <slot :name="`cell-${c.key}`" :row="row" :value="value(row, c.key)">{{ value(row, c.key) ?? '—' }}</slot>
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-if="!loading && !rows.length" :title="emptyTitle" :message="emptyMessage">
        <slot name="empty" />
      </EmptyState>
    </div>
    <Pagination v-if="total !== undefined && page && pageSize && total > 0" :page="page" :page-size="pageSize" :total="total" @change="emit('page', $event)" />
  </div>
</template>
