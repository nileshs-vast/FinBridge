import { NavLink, useNavigate } from 'react-router-dom'
import {
  Building2,
  Users,
  Upload,
  List,
  FileText,
  LayoutDashboard,
  LogOut,
  PenLine,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const navByRole: Record<string, { to: string; label: string; icon: React.ReactNode }[]> = {
  platform_admin: [
    { to: '/platform/firms', label: 'Firms', icon: <Building2 size={18} /> },
  ],
  firm_admin: [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { to: '/firm/companies', label: 'Companies', icon: <Building2 size={18} /> },
    { to: '/firm/team', label: 'Team', icon: <Users size={18} /> },
  ],
  accountant: [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { to: '/accountant/queue', label: 'Review Queue', icon: <List size={18} /> },
    { to: '/accountant/reports', label: 'Reports', icon: <FileText size={18} /> },
  ],
  company_user: [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { to: '/company/upload', label: 'Upload', icon: <Upload size={18} /> },
    { to: '/company/manual', label: 'Manual Entry', icon: <PenLine size={18} /> },
    { to: '/company/transactions', label: 'Transactions', icon: <List size={18} /> },
    { to: '/company/reports', label: 'Reports', icon: <FileText size={18} /> },
  ],
}

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const links = user ? (navByRole[user.role] ?? []) : []

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-60 flex-shrink-0 bg-slate-800 flex flex-col h-screen">
      <div className="px-6 py-5 border-b border-slate-700">
        <span className="text-white text-xl font-bold tracking-tight">FinBridge</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-700 hover:text-white'
              )
            }
          >
            {icon}
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-slate-700">
        <div className="mb-3 px-1">
          <p className="text-xs text-slate-400 truncate">{user?.email}</p>
          <p className="text-xs text-slate-500 capitalize">{user?.role?.replace(/_/g, ' ')}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 px-3 py-2 rounded-md text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
