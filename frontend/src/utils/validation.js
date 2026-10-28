// Client-side checks that mirror the server's rules (the server always re-checks).
export function passwordProblem(p) {
  if (!p) return 'Enter a password'
  if (p.length < 8) return 'Use at least 8 characters'
  if (p.length > 128) return 'Use at most 128 characters'
  if (!/[A-Z]/.test(p)) return 'Add at least one upper-case letter'
  if (!/\d/.test(p)) return 'Add at least one digit'
  return ''
}
export const isEmail = (v) => /^\S+@\S+\.\S+$/.test((v || '').trim())
export const isUrl = (v) => /^https?:\/\/\S+\.\S+/.test((v || '').trim())

/** Copy server-side field errors (error.details) into a reactive errors object. */
export function applyServerErrors(errors, err) {
  if (!err?.details) return false
  for (const [key, msgs] of Object.entries(err.details)) errors[key.split('.').pop()] = msgs[0]
  return true
}
