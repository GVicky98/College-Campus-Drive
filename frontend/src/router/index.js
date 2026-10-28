import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/layouts/AppShell.vue'

// Route meta:
//   public: true      only for signed-out visitors (login, password reset)
//   role: 'student'   the area requires this role
//   perm: 'x' | []    the page requires ANY of these permissions (otherwise an in-layout "access denied")
const NotFound = () => import('@/pages/auth/NotFound.vue')

const Documents = () => import('@/pages/shared/Documents.vue')
const Settings = () => import('@/pages/shared/Settings.vue')
const Notifications = () => import('@/pages/shared/Notifications.vue')

const studentRoutes = [
  { path: 'dashboard', component: () => import('@/pages/student/Dashboard.vue') },
  { path: 'profile', component: () => import('@/pages/student/Profile.vue') },
  { path: 'jobs', component: () => import('@/pages/student/Jobs.vue') },
  { path: 'jobs/:jobId', component: () => import('@/pages/student/JobDetail.vue') },
  { path: 'applications', component: () => import('@/pages/student/Applications.vue') },
  { path: 'applications/:applicationId', component: () => import('@/pages/student/ApplicationDetail.vue') },
  { path: 'offers', component: () => import('@/pages/student/Offers.vue') },
  { path: 'assistant', component: () => import('@/pages/shared/Assistant.vue') },
  { path: 'reminders', component: () => import('@/pages/student/Reminders.vue') },
  { path: 'documents', component: Documents },
  { path: 'settings', component: Settings },
]

const F = {
  Dashboard: () => import('@/pages/faculty/Dashboard.vue'),
  Companies: () => import('@/pages/faculty/Companies.vue'),
  CompanyDetail: () => import('@/pages/faculty/CompanyDetail.vue'),
  Jobs: () => import('@/pages/faculty/Jobs.vue'),
  JobForm: () => import('@/pages/faculty/JobForm.vue'),
  JobDetail: () => import('@/pages/faculty/JobDetail.vue'),
  Drives: () => import('@/pages/faculty/Drives.vue'),
  Students: () => import('@/pages/faculty/Students.vue'),
  StudentDetail: () => import('@/pages/faculty/StudentDetail.vue'),
  Applications: () => import('@/pages/faculty/Applications.vue'),
  Interviews: () => import('@/pages/faculty/Interviews.vue'),
  Offers: () => import('@/pages/faculty/Offers.vue'),
  Reports: () => import('@/pages/faculty/Reports.vue'),
}

const facultyRoutes = [
  { path: 'dashboard', component: F.Dashboard },
  { path: 'companies', component: F.Companies, meta: { perm: 'companies.manage' } },
  { path: 'companies/:companyId', component: F.CompanyDetail, meta: { perm: 'companies.manage' } },
  { path: 'jobs', component: F.Jobs, meta: { perm: 'jobs.create' } },
  { path: 'jobs/new', component: F.JobForm, meta: { perm: 'jobs.create' } },
  { path: 'jobs/:jobId', component: F.JobDetail, meta: { perm: 'jobs.create' } },
  { path: 'jobs/:jobId/edit', component: F.JobForm, meta: { perm: 'jobs.create' } },
  { path: 'drives', component: F.Drives, meta: { perm: 'jobs.create' } },
  { path: 'students', component: F.Students, meta: { perm: 'students.view' } },
  { path: 'students/:studentId', component: F.StudentDetail, meta: { perm: 'students.view' } },
  { path: 'applications', component: F.Applications, meta: { perm: 'applications.review' } },
  { path: 'interviews', component: F.Interviews, meta: { perm: 'applications.review' } },
  { path: 'offers', component: F.Offers, meta: { perm: 'offers.manage' } },
  { path: 'documents', component: Documents },
  { path: 'assistant', component: () => import('@/pages/shared/Assistant.vue') },
  { path: 'reports', component: F.Reports, meta: { perm: 'reports.view' } },
  { path: 'notifications', component: Notifications },
  { path: 'settings', component: Settings },
]

const A = {
  Dashboard: () => import('@/pages/admin/Dashboard.vue'),
  Users: () => import('@/pages/admin/Users.vue'),
  Roles: () => import('@/pages/admin/Roles.vue'),
  StudentsFaculty: () => import('@/pages/admin/StudentsFaculty.vue'),
  CompaniesJobs: () => import('@/pages/admin/CompaniesJobs.vue'),
  Policies: () => import('@/pages/admin/Policies.vue'),
  Departments: () => import('@/pages/admin/Departments.vue'),
  AuditLogs: () => import('@/pages/admin/AuditLogs.vue'),
  Settings: () => import('@/pages/admin/SystemSettings.vue'),
}

const adminRoutes = [
  { path: 'dashboard', component: A.Dashboard },
  { path: 'users', component: A.Users, meta: { perm: 'users.manage' } },
  { path: 'roles', component: A.Roles, meta: { perm: 'roles.manage' } },
  { path: 'students', component: A.StudentsFaculty, meta: { perm: 'students.view' } },
  { path: 'faculty', component: A.StudentsFaculty, meta: { perm: 'students.view' } },
  { path: 'students/:studentId', component: F.StudentDetail, meta: { perm: 'students.view' } },
  { path: 'companies', component: A.CompaniesJobs, meta: { perm: ['companies.manage', 'jobs.create', 'applications.review', 'students.view'] } },
  { path: 'companies/:companyId', component: F.CompanyDetail, meta: { perm: ['companies.manage', 'jobs.create', 'applications.review', 'students.view'] } },
  { path: 'jobs', component: A.CompaniesJobs, meta: { perm: ['jobs.create', 'applications.review', 'students.view', 'drives.publish'] } },
  { path: 'jobs/new', component: F.JobForm, meta: { perm: 'jobs.create' } },
  { path: 'jobs/:jobId', component: F.JobDetail, meta: { perm: ['jobs.create', 'drives.publish', 'applications.review'] } },
  { path: 'jobs/:jobId/edit', component: F.JobForm, meta: { perm: 'jobs.create' } },
  { path: 'drives', component: F.Drives, meta: { perm: 'jobs.create' } },
  { path: 'applications', component: F.Applications, meta: { perm: 'applications.review' } },
  { path: 'interviews', component: F.Interviews, meta: { perm: 'applications.review' } },
  { path: 'offers', component: F.Offers, meta: { perm: 'offers.manage' } },
  { path: 'policies', component: A.Policies, meta: { perm: 'policies.manage' } },
  { path: 'departments', component: A.Departments },
  { path: 'documents', component: Documents },
  { path: 'assistant', component: () => import('@/pages/shared/Assistant.vue') },
  { path: 'reports', component: F.Reports, meta: { perm: 'reports.view' } },
  { path: 'audit-logs', component: A.AuditLogs, meta: { perm: 'audit.view' } },
  { path: 'notifications', component: Notifications },
  { path: 'settings', component: A.Settings },
]

function area(role, children) {
  return {
    path: `/${role}`,
    component: AppShell,
    meta: { role },
    children: [{ path: '', redirect: `/${role}/dashboard` }, ...children, { path: ':rest(.*)*', component: NotFound }],
  }
}

const routes = [
  { path: '/', redirect: () => useAuthStore().home },
  { path: '/login', component: () => import('@/pages/auth/Login.vue'), meta: { public: true } },
  { path: '/forgot-password', component: () => import('@/pages/auth/ForgotPassword.vue'), meta: { public: true } },
  { path: '/reset-password', component: () => import('@/pages/auth/ResetPassword.vue'), meta: { public: true } },
  { path: '/forbidden', component: () => import('@/pages/auth/Forbidden.vue') },
  { path: '/student/onboarding', component: () => import('@/pages/student/Onboarding.vue'), meta: { role: 'student', onboarding: true } },
  area('student', studentRoutes),
  area('faculty', facultyRoutes),
  area('admin', adminRoutes),
  { path: '/:rest(.*)*', component: NotFound },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved || (to.path !== from.path ? { top: 0 } : undefined),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.init()

  if (to.meta.public) {
    if (!auth.isSignedIn) return true
    const from = to.query.from
    return typeof from === 'string' && from.startsWith(`/${auth.role}`) ? from : auth.home
  }

  const role = to.matched.find((r) => r.meta.role)?.meta.role
  if (!role) return true
  if (!auth.isSignedIn) return { path: '/login', query: { from: to.fullPath } }
  if (auth.role !== role) return { path: '/forbidden' }

  // Students finish onboarding before anything else.
  const onboarded = auth.user.onboardingComplete !== false
  if (role === 'student' && !onboarded && !to.meta.onboarding) return '/student/onboarding'
  if (to.meta.onboarding && onboarded) return '/student/dashboard'
  return true
})

// Signed out elsewhere (expired session, deactivated account): go to the login page.
window.addEventListener('ca:unauthorized', () => {
  const auth = useAuthStore()
  if (!auth.isSignedIn) return
  auth.clear()
  const current = router.currentRoute.value
  if (!current.meta.public) router.replace({ path: '/login', query: { from: current.fullPath } })
})

export default router
