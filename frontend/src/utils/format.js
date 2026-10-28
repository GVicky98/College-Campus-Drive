// Display helpers shared by every page.

const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
const shortFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })
const timeFmt = new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' })

const toDate = (v) => (v instanceof Date ? v : new Date(v))

export const formatDate = (v) => (v ? dateFmt.format(toDate(v)) : '—')
export const formatDateTime = (v) => (v ? dateTimeFmt.format(toDate(v)) : '—')
export const formatShortDate = (v) => (v ? shortFmt.format(toDate(v)) : '—')
export const formatTime = (v) => (v ? timeFmt.format(toDate(v)) : '—')

export function timeAgo(v) {
  if (!v) return '—'
  const seconds = Math.round((Date.now() - toDate(v).getTime()) / 1000)
  const future = seconds < 0
  const s = Math.abs(seconds)
  const units = [['year', 31536000], ['month', 2592000], ['week', 604800], ['day', 86400], ['hour', 3600], ['minute', 60]]
  for (const [name, size] of units) {
    if (s >= size) {
      const n = Math.floor(s / size)
      const label = `${n} ${name}${n > 1 ? 's' : ''}`
      return future ? `in ${label}` : `${label} ago`
    }
  }
  return future ? 'in a moment' : 'just now'
}

/** Whole days from now until `v` (negative when past). */
export function daysUntil(v) {
  if (!v) return null
  return Math.ceil((toDate(v).getTime() - Date.now()) / 86400000)
}

export function formatPackage(ctcLpa, stipend) {
  if (ctcLpa) return `₹${Number(ctcLpa).toLocaleString('en-IN', { maximumFractionDigits: 2 })} LPA`
  if (stipend) return `₹${Number(stipend).toLocaleString('en-IN')}/month`
  return '—'
}

export const formatNumber = (n) => (n === null || n === undefined ? '—' : Number(n).toLocaleString('en-IN'))
export const formatCgpa = (n) => (n === null || n === undefined ? '—' : Number(n).toFixed(2))

export function initials(name = '') {
  return name
    .replace(/^(Dr|Prof|Mr|Ms|Mrs)\.?\s+/i, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

export const titleCase = (s = '') => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
export const sentenceCase = (s = '') => { const t = s.replace(/_/g, ' '); return t.charAt(0).toUpperCase() + t.slice(1) }

export const ROLE_LABEL = { student: 'Student', faculty: 'Faculty / Placement Officer', admin: 'Administrator' }
export const TIER_LABEL = { regular: 'Regular', dream: 'Dream', super_dream: 'Super Dream' }

/** "YYYY-MM-DDTHH:mm" in local time, for <input type="datetime-local">. */
export function toLocalInput(v) {
  if (!v) return ''
  const d = toDate(v)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
export const toLocalDateInput = (v) => toLocalInput(v).slice(0, 10)
/** Local input value -> ISO UTC string for the API. */
export const fromLocalInput = (v) => (v ? new Date(v).toISOString() : null)

/** CSV text -> file download. Cells starting with = + - @ are prefixed so spreadsheets don't run them. */
export function toCsv(columns, rows) {
  const safe = (v) => {
    let s = v === null || v === undefined ? '' : String(v)
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s
    return `"${s.replace(/"/g, '""')}"`
  }
  return [columns.map(safe).join(','), ...rows.map((r) => r.map(safe).join(','))].join('\r\n')
}

export function downloadText(filename, text, type = 'text/csv;charset=utf-8') {
  const blob = new Blob([text], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export const slugify = (s = 'export') => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'export'

/** The server's { label, at? } next-step hint, as text in local time. */
export const formatNextAction = (n) => (!n ? '—' : n.at ? `${n.label} · ${formatDateTime(n.at)}` : n.label)
