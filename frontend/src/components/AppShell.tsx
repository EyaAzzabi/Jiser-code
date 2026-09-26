import clsx from 'clsx'
import { Home, LogOut, Menu, Sparkles, X, type LucideIcon } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { authApi, ROLE_LABELS, saveSession, type Session } from '../api'
import NotificationBell from './NotificationBell'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
  ai?: boolean
}

function structureOf(session: Session): string {
  const d = session.utilisateur?.details ?? {}
  if (d.centre) return `CRCI ${String(d.centre)}`
  return String(d.raison_sociale ?? d.cabinet ?? d.structure ?? '') + (d.gouvernorat ? ` · ${String(d.gouvernorat)}` : '')
}

export default function AppShell({ session, espace, nav, children }: {
  session: Session
  espace: string
  nav: NavItem[]
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { pathname } = useLocation()
  useEffect(() => { setOpen(false); window.scrollTo(0, 0) }, [pathname])

  const logout = async () => {
    try { await authApi.deconnexion() } catch { /* session already gone */ }
    saveSession(null)
    navigate('/')
  }
  const u = session.utilisateur
  const name = u ? `${u.prenom} ${u.nom}` : session.role === 'admin' ? 'Administrateur' : ''

  const sidebar = (
    <div className="flex h-full flex-col">
      <Link to="/" className="flex items-center gap-2.5 px-5 py-5">
        <img src="/logo-icon.png" alt="Logo JISER" className="h-10 w-10" />
        <div className="leading-tight">
          <div className="font-display text-lg font-extrabold text-navy-900">J<span className="text-gold">i</span>SER <span className="font-sans font-normal text-gold">جسر</span></div>
          <div className="text-[11px] font-medium text-gold-dark">{espace}</div>
        </div>
      </Link>

      <div className="mx-4 rounded-2xl border border-gold/30 bg-gold-light/50 p-3">
        <div className="text-[11px] uppercase tracking-wide text-slate-500">Connecté</div>
        <div className="font-semibold text-navy-900">{name}</div>
        <div className="text-xs font-medium text-gold-dark">{ROLE_LABELS[session.role ?? ''] ?? ''}</div>
        {structureOf(session) && <div className="mt-0.5 truncate text-xs text-slate-500">{structureOf(session)}</div>}
      </div>

      <nav className="mt-5 flex-1 space-y-1 px-3">
        {nav.map(({ to, label, icon: Icon, end, ai }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => clsx('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
              isActive ? 'bg-bridge-light text-navy-900 ring-1 ring-bridge/20' : 'text-slate-600 hover:bg-slate-100 hover:text-navy-900')}>
            <Icon size={18} className="shrink-0" />
            <span className="flex-1">{label}</span>
            {ai && <span className="flex items-center gap-0.5 rounded-md bg-gold px-1.5 py-0.5 text-[10px] font-bold text-white"><Sparkles size={10} />IA</span>}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-1 border-t border-slate-200 p-3">
        <Link to="/" className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"><Home size={18} /> Retour à l'accueil</Link>
        <button onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-rose-50 hover:text-rose-700"><LogOut size={18} /> Se déconnecter</button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block">{sidebar}</aside>
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Link to="/" className="flex items-center gap-2"><img src="/logo-icon.png" alt="" className="h-8 w-8" /><span className="font-display font-bold text-navy-900">JISER</span></Link>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <button onClick={() => setOpen(true)} aria-label="Ouvrir le menu" className="rounded-lg p-2 hover:bg-slate-100"><Menu /></button>
        </div>
      </div>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-navy-950/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white shadow-xl">
            <button onClick={() => setOpen(false)} aria-label="Fermer le menu" className="absolute right-3 top-4 rounded-lg p-1 hover:bg-slate-100"><X size={18} /></button>
            {sidebar}
          </aside>
        </div>
      )}
      <main className="px-4 py-6 lg:ml-64 lg:px-10">
        <div className="mb-2 hidden justify-end lg:flex"><NotificationBell /></div>
        {children}
      </main>
    </div>
  )
}
