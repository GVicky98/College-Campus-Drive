// Sidebar navigation per role. `perm` hides an item unless the user holds that permission.
import {
  Bell, Bot, Briefcase, Building2, CalendarDays, ChartColumn, ClipboardList, Folder, Gavel, Gift, Handshake, History,
  Landmark, LayoutDashboard, Settings, ShieldCheck, SlidersHorizontal, UserCog, UserRound, Users,
} from '@lucide/vue'

export const NAV = {
  student: [
    { label: 'Dashboard', to: '/student/dashboard', icon: LayoutDashboard },
    { label: 'My Profile', to: '/student/profile', icon: UserRound },
    { label: 'Jobs & Opportunities', to: '/student/jobs', icon: Briefcase },
    { label: 'My Applications', to: '/student/applications', icon: ClipboardList },
    { label: 'My Offers', to: '/student/offers', icon: Gift },
    { label: 'AI Assistant', to: '/student/assistant', icon: Bot },
    { label: 'Reminders & Notifications', to: '/student/reminders', icon: Bell },
    { label: 'Documents', to: '/student/documents', icon: Folder },
    { label: 'Settings', to: '/student/settings', icon: Settings },
  ],
  faculty: [
    { label: 'Dashboard', to: '/faculty/dashboard', icon: LayoutDashboard },
    { label: 'Companies', to: '/faculty/companies', icon: Building2, perm: 'companies.manage' },
    { label: 'Jobs & Hiring Drives', to: '/faculty/jobs', icon: Briefcase, perm: 'jobs.create' },
    { label: 'Students', to: '/faculty/students', icon: Users, perm: 'students.view' },
    { label: 'Applications & Applicants', to: '/faculty/applications', icon: ClipboardList, perm: 'applications.review' },
    { label: 'Interviews & Selection', to: '/faculty/interviews', icon: CalendarDays, perm: 'applications.review' },
    { label: 'Offers & Placements', to: '/faculty/offers', icon: Handshake, perm: 'offers.manage' },
    { label: 'Documents & Circulars', to: '/faculty/documents', icon: Folder },
    { label: 'AI Assistant', to: '/faculty/assistant', icon: Bot },
    { label: 'Placement Reports', to: '/faculty/reports', icon: ChartColumn, perm: 'reports.view' },
    { label: 'Notifications', to: '/faculty/notifications', icon: Bell },
    { label: 'Settings', to: '/faculty/settings', icon: Settings },
  ],
  admin: [
    { label: 'Dashboard', to: '/admin/dashboard', icon: LayoutDashboard },
    { label: 'User Management', to: '/admin/users', icon: UserCog, perm: 'users.manage' },
    { label: 'Roles & Permissions', to: '/admin/roles', icon: ShieldCheck, perm: 'roles.manage' },
    { label: 'Students & Faculty', to: '/admin/students', icon: Users, perm: 'students.view' },
    { label: 'Companies & Jobs', to: '/admin/companies', icon: Building2 },
    { label: 'Placement Policies', to: '/admin/policies', icon: Gavel, perm: 'policies.manage' },
    { label: 'Departments & Courses', to: '/admin/departments', icon: Landmark },
    { label: 'Documents', to: '/admin/documents', icon: Folder },
    { label: 'AI Assistant', to: '/admin/assistant', icon: Bot },
    { label: 'Reports & Analytics', to: '/admin/reports', icon: ChartColumn, perm: 'reports.view' },
    { label: 'Audit Logs', to: '/admin/audit-logs', icon: History, perm: 'audit.view' },
    { label: 'Notifications', to: '/admin/notifications', icon: Bell },
    { label: 'System Settings', to: '/admin/settings', icon: SlidersHorizontal },
  ],
}

// Where the top-bar search box sends its query, per role.
export const TOP_SEARCH = {
  student: { to: '/student/jobs', placeholder: 'Search jobs, companies, skills' },
  faculty: { to: '/faculty/students', placeholder: 'Search students by name or ID' },
  admin: { to: '/admin/users', placeholder: 'Search users by name or e-mail' },
}
