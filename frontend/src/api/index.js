// Every backend endpoint, grouped by area. Pages import from here, never call axios directly.
import { api } from './http'

export const authApi = {
  login: (body) => api.post('/auth/login', body, { auth: false }),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  changePassword: (body) => api.post('/auth/change-password', body),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }, { auth: false }),
  resetPassword: (token, password) => api.post('/auth/reset-password', { token, password }, { auth: false }),
}

export const referenceApi = {
  filters: () => api.get('/reference/filters'),
}

export const studentApi = {
  profile: () => api.get('/student/profile'),
  updateProfile: (patch) => api.patch('/student/profile', patch),
  onboarding: (body) => api.post('/student/onboarding', body),
  dashboard: () => api.get('/student/dashboard'),
}

export const jobsApi = {
  list: (params) => api.page('/jobs', params),
  get: (id) => api.get(`/jobs/${id}`),
  toggleSave: (id) => api.post(`/jobs/${id}/save`),
  create: (body) => api.post('/jobs', body),
  update: (id, body) => api.put(`/jobs/${id}`, body),
  setStatus: (id, status, reason) => api.post(`/jobs/${id}/status`, { status, reason }),
  archive: (id, archived) => api.post(`/jobs/${id}/archive`, { archived }),
  drive: (id) => api.get(`/jobs/${id}/drive`),
}

export const applicationsApi = {
  apply: (jobId) => api.post('/applications', { jobId }),
  mine: (params) => api.page('/applications/me', params),
  get: (id) => api.get(`/applications/${id}`),
  withdraw: (id) => api.post(`/applications/${id}/withdraw`),
  list: (params) => api.page('/applications', params),
  updateStage: (body) => api.post('/applications/stage', body),
  exportCsv: (params) => api.get('/applications/export', params),
}

export const interviewsApi = {
  list: (params) => api.page('/interviews', params),
  create: (body) => api.post('/interviews', body),
  update: (id, body) => api.put(`/interviews/${id}`, body),
  setStatus: (id, status) => api.post(`/interviews/${id}/status`, { status }),
  notify: (id) => api.post(`/interviews/${id}/notify`),
}

export const offersApi = {
  mine: () => api.get('/offers/me'),
  policies: () => api.get('/offers/policies'),
  respond: (id, decision) => api.post(`/offers/${id}/respond`, { decision }),
  list: (params) => api.page('/offers', params),
  create: (body) => api.post('/offers', body),
  setStatus: (id, status, reason) => api.post(`/offers/${id}/status`, { status, reason }),
}

export const companiesApi = {
  list: (params) => api.page('/companies', params),
  get: (id) => api.get(`/companies/${id}`),
  create: (body) => api.post('/companies', body),
  update: (id, body) => api.put(`/companies/${id}`, body),
  archive: (id, archived) => api.post(`/companies/${id}/archive`, { archived }),
}

export const studentsApi = {
  list: (params) => api.page('/students', params),
  get: (id) => api.get(`/students/${id}`),
  verifyCgpa: (id, cgpa) => api.post(`/students/${id}/verify-cgpa`, cgpa === undefined ? {} : { cgpa }),
}

export const usersApi = {
  list: (params) => api.page('/users', params),
  create: (body) => api.post('/users', body),
  update: (id, body) => api.put(`/users/${id}`, body),
  setStatus: (id, status) => api.post(`/users/${id}/status`, { status }),
  resetPassword: (id) => api.post(`/users/${id}/reset-password`),
  importStudents: (rows) => api.post('/users/import', { rows }),
}

export const notificationsApi = {
  list: () => api.get('/notifications'),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
  preferences: () => api.get('/notifications/preferences'),
  savePreferences: (prefs) => api.put('/notifications/preferences', prefs),
}

export const remindersApi = {
  list: () => api.get('/reminders'),
  create: (body) => api.post('/reminders', body),
  update: (id, body) => api.put(`/reminders/${id}`, body),
  toggle: (id) => api.post(`/reminders/${id}/toggle`),
  remove: (id) => api.del(`/reminders/${id}`),
}

export const documentsApi = {
  list: (params) => api.page('/documents', params),
  get: (id) => api.get(`/documents/${id}`),
  upload: (formData) => api.upload('/documents', formData),
  replace: (id, formData) => api.upload(`/documents/${id}/replace`, formData),
  reprocess: (id) => api.post(`/documents/${id}/reprocess`),
  remove: (id) => api.del(`/documents/${id}`),
  file: (id) => api.blob(`/documents/${id}/file`),
}

export const reportsApi = {
  facultyDashboard: (params) => api.get('/faculty/dashboard', params),
  placement: (params) => api.get('/reports/placement', params),
  exportPlacement: (params) => api.get('/reports/placement/export.csv', params),
}

export const adminApi = {
  dashboard: () => api.get('/admin/dashboard'),
  roles: () => api.get('/admin/roles'),
  setPermission: (role, perm, enabled) => api.put(`/admin/roles/${role}/permissions/${perm}`, { enabled }),
  policies: () => api.get('/admin/policies'),
  createPolicy: (body) => api.post('/admin/policies', body),
  updatePolicy: (id, body) => api.put(`/admin/policies/${id}`, body),
  deletePolicy: (id, reason) => api.del(`/admin/policies/${id}`, { reason }),
  academic: () => api.get('/admin/academic'),
  saveDepartment: (id, body) => (id ? api.put(`/admin/departments/${id}`, body) : api.post('/admin/departments', body)),
  deleteDepartment: (id) => api.del(`/admin/departments/${id}`),
  saveCourse: (id, body) => (id ? api.put(`/admin/courses/${id}`, body) : api.post('/admin/courses', body)),
  deleteCourse: (id) => api.del(`/admin/courses/${id}`),
  saveYear: (id, body) => (id ? api.put(`/admin/academic-years/${id}`, body) : api.post('/admin/academic-years', body)),
  auditLogs: (params) => api.page('/admin/audit-logs', params),
  settings: () => api.get('/admin/settings'),
  saveSettings: (body) => api.put('/admin/settings', body),
  publicSettings: () => api.get('/settings/public', undefined, { auth: false }),
}

export const assistantApi = {
  status: () => api.get('/assistant/status'),
  suggestions: () => api.get('/assistant/suggestions'),
  conversations: () => api.get('/assistant/conversations'),
  conversation: (id) => api.get(`/assistant/conversations/${id}`),
  remove: (id) => api.del(`/assistant/conversations/${id}`),
  chat: (message, conversationId) => api.post('/assistant/chat', { message, conversationId }, { timeout: 120000 }),
  confirm: (id) => api.post(`/assistant/actions/${id}/confirm`),
  reject: (id) => api.post(`/assistant/actions/${id}/reject`),
}
