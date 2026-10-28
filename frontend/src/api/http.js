// The one axios instance every API call goes through.
//
// Session design:
//  - the short-lived access token lives ONLY in memory (this module), never in localStorage;
//  - the refresh token is an httpOnly cookie the browser sends to /api/v1/auth/*;
//  - refresh calls echo the readable `csrf_refresh_token` cookie in the X-CSRF-TOKEN header (double submit);
//  - a 401 triggers one refresh (shared by concurrent requests) and one retry; if that fails we sign out.
import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

let accessToken = null
export const setAccessToken = (token) => { accessToken = token }
export const getAccessToken = () => accessToken

/** Normalised error thrown by every API helper. */
export class ApiError extends Error {
  constructor(status, message, code = 'error', details = undefined) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
  headers: { Accept: 'application/json' },
  // Repeat array keys: ?ids=1&ids=2 and drop empty values.
  paramsSerializer: { serialize: buildQuery },
})

export function buildQuery(params = {}) {
  const q = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => q.append(key, v))
    else q.append(key, value)
  }
  return q.toString()
}

function readCookie(name) {
  const match = document.cookie.split('; ').find((c) => c.startsWith(name + '='))
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : null
}

export const hasSessionCookie = () => Boolean(readCookie('csrf_refresh_token'))

// ---- refresh (single flight)
let refreshing = null
export function refreshSession() {
  if (!hasSessionCookie()) return Promise.resolve(null)
  if (!refreshing) {
    refreshing = axios
      .post(`${API_BASE_URL}/auth/refresh`, null, {
        withCredentials: true,
        headers: { 'X-CSRF-TOKEN': readCookie('csrf_refresh_token') },
      })
      .then((r) => {
        setAccessToken(r.data.data.accessToken)
        return r.data.data
      })
      .catch(() => {
        setAccessToken(null)
        return null
      })
      .finally(() => { refreshing = null })
  }
  return refreshing
}

http.interceptors.request.use((config) => {
  if (accessToken && config.auth !== false) config.headers.Authorization = `Bearer ${accessToken}`
  if (config.url?.startsWith('/auth/')) config.headers['X-CSRF-TOKEN'] = readCookie('csrf_refresh_token') || ''
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthCall = config?.url?.startsWith('/auth/login') || config?.url?.startsWith('/auth/refresh')
    if (response?.status === 401 && config && !config._retried && !isAuthCall && config.auth !== false) {
      config._retried = true
      const session = await refreshSession()
      if (session) return http(config)
      setAccessToken(null)
      window.dispatchEvent(new Event('ca:unauthorized'))
    }
    throw toApiError(error)
  },
)

function toApiError(error) {
  if (error instanceof ApiError) return error
  if (!error.response) {
    if (error.code === 'ECONNABORTED') return new ApiError(0, 'The request took too long. Please try again.', 'timeout')
    return new ApiError(0, 'Cannot reach the server. Check your connection and try again.', 'network_error')
  }
  const { status, data } = error.response
  const e = data?.error
  if (e?.message) return new ApiError(status, e.message, e.code, e.details)
  if (status >= 500) return new ApiError(status, 'The server ran into a problem. Please try again.', 'server_error')
  return new ApiError(status, 'The request failed.', 'error')
}

// ---- helpers that unwrap the {data} / {data, meta} envelopes
function unwrap(response) {
  if (!response.data || !('data' in response.data)) throw new ApiError(502, 'Unexpected response from the server.', 'bad_response')
  return response.data.data
}

export const api = {
  get: (url, params, config = {}) => http.get(url, { ...config, params }).then(unwrap),
  post: (url, body, config = {}) => http.post(url, body ?? {}, config).then(unwrap),
  put: (url, body, config = {}) => http.put(url, body ?? {}, config).then(unwrap),
  patch: (url, body, config = {}) => http.patch(url, body ?? {}, config).then(unwrap),
  del: (url, body, config = {}) => http.delete(url, { ...config, data: body }).then(unwrap),
  /** Paginated GET: returns { items, total, page, pageSize, totalPages, meta }. */
  page: (url, params, config = {}) =>
    http.get(url, { ...config, params }).then((r) => {
      const items = unwrap(r)
      const meta = r.data.meta || {}
      return { items, total: meta.total ?? items.length, page: meta.page ?? 1, pageSize: meta.pageSize ?? items.length, totalPages: meta.totalPages ?? 1, meta }
    }),
  /** GET a file as a Blob (sends the Authorization header, unlike a plain link). */
  blob: (url, config = {}) => http.get(url, { ...config, responseType: 'blob' }).then((r) => r.data),
  upload: (url, formData, config = {}) => http.post(url, formData, { ...config, headers: { 'Content-Type': 'multipart/form-data' } }).then(unwrap),
}

export default http
