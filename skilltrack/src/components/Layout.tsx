import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { Role } from '../context/AuthContext'
import { Logo } from './AuthLayout'

const NAV: Record<Role, { to: string; label: string }[]> = {
  student: [
    { to: '/student', label: 'Dashboard' },
    { to: '/exam', label: 'Take Exam' },
  ],
  owner: [{ to: '/owner', label: 'Track Overview' }],
  admin: [
    { to: '/admin', label: 'Analytics' },
    { to: '/invigilator', label: 'Exam Keys' },
  ],
  invigilator: [{ to: '/invigilator', label: 'Exam Keys' }],
}

const ROLE_LABEL: Record<Role, string> = {
  student: 'Student', owner: 'Track Owner', admin: 'Admin', invigilator: 'Invigilator',
}

export default function Layout() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  if (loading) return <div className="p-6 text-sm text-gray-500">Loading…</div>
  if (!user) return <Navigate to="/login" replace />

  function signOut() {
    logout()
    navigate('/login', { replace: true })
  }

  const initial = user.name.trim().charAt(0).toUpperCase()

  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-800">
      <aside className="relative flex w-60 shrink-0 flex-col overflow-hidden border-r border-white/10 bg-slate-950 p-5 text-white">
        {/* Aurora Glows for the whole sidebar */}
        <div className="pointer-events-none absolute -left-20 -top-20 h-64 w-64 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-1/4 h-80 w-80 rounded-full bg-purple-600/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl" />
        
        <div className="relative z-10">
          <div className="mb-8"><Logo /></div>
          <nav className="space-y-1">
            {NAV[user.role].map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  `block rounded-xl px-3 py-2.5 text-sm font-semibold transition-all ${isActive ? 'bg-indigo-500/20 text-indigo-200 shadow-sm ring-1 ring-inset ring-indigo-500/30' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Minimal Footer */}
        <div className="relative z-10 mt-auto">
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-indigo-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></span>
            Live System
          </div>
          <p className="mt-1 text-xs font-medium text-slate-400">
            SkillTrack Cloud
          </p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">{ROLE_LABEL[user.role]}</span>
          <div className="flex items-center gap-3 text-sm">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-50 text-sm font-bold text-indigo-700 ring-1 ring-inset ring-indigo-600/20">{initial}</span>
            <span className="font-bold text-slate-800">{user.name}</span>
            <button onClick={signOut} className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold text-slate-500 transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-800">Sign out</button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
