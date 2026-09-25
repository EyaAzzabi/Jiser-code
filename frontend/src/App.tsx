import clsx from 'clsx'
import { BadgeCheck, Building2, Compass, Landmark, LogOut, Settings, Sparkles, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api, authApi, loadSession, saveSession, type SessionInfo, type Status } from './api'
import Onboarding, { shouldShowOnboarding } from './components/Onboarding'
import Administration from './pages/Administration'
import AdminPlateforme from './pages/AdminPlateforme'
import Entreprise from './pages/Entreprise'
import Home from './pages/Home'

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <img src="/logo-icon.png" alt="Logo JISER" className="h-11 w-11" />
      <div className="leading-tight">
        <div className="font-display text-xl font-extrabold tracking-wide text-navy-900">J<span className="text-gold">i</span>SER <span className="font-sans font-normal text-gold">جسر</span></div>
        <div className="hidden text-[11px] text-slate-500 sm:block">Le pont entre le contribuable et l'administration fiscale</div>
      </div>
    </Link>
  )
}

const NAV = [
  { to: '/entreprise', label: 'Entreprise', icon: Building2 },
  { to: '/administration', label: 'Administration', icon: Landmark },
  { to: '/plateforme', label: 'Plateforme', icon: Settings },
]

function AiStatus({ status }: { status: Status | null }) {
  if (!status) return null
  return status.llm.ia ? (
    <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
      <Sparkles size={14} /> IA active
    </span>
  ) : (
    <span title={status.llm.raison} className="flex items-center gap-1.5 rounded-full bg-gold-light px-3 py-1 text-xs font-medium text-gold-dark ring-1 ring-gold/40">
      <WifiOff size={14} /> Mode hors ligne
    </span>
  )
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null)
  const [onboarding, setOnboarding] = useState(() => shouldShowOnboarding() && !window.location.search.includes('noguide'))
  const [session, setSession] = useState<SessionInfo | null>(loadSession())
  const { pathname } = useLocation()
  const logout = () => {
    if (session) authApi.deconnexion(session.token).catch(() => {})
    saveSession(null); setSession(null)
  }
  useEffect(() => {
    api.status().then(setStatus).catch(() => setStatus(null))
  }, [])
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-2.5">
          <Logo />
          <nav className="flex flex-wrap items-center gap-1">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to}
                className={({ isActive }) => clsx(
                  'relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition',
                  isActive ? 'text-navy-900 after:absolute after:inset-x-3 after:-bottom-[11px] after:h-0.5 after:rounded-full after:bg-gold' : 'text-slate-600 hover:bg-slate-100 hover:text-navy-900',
                )}>
                <Icon size={16} /> {label}
              </NavLink>
            ))}
            {session ? (
              <div className="ml-2 flex items-center gap-2 rounded-full bg-canvas py-1 pl-1 pr-2 ring-1 ring-slate-200">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-navy-900 text-xs font-bold text-white">
                  {session.profil.prenom[0]}{session.profil.nom[0]}
                </span>
                <span className="text-sm font-medium text-navy-900">{session.profil.prenom}</span>
                <BadgeCheck size={16} className="text-gold" aria-label="Identité vérifiée par OTP" />
                <button onClick={logout} title="Se déconnecter" className="rounded-full p-1 text-slate-400 hover:bg-white hover:text-navy-900"><LogOut size={14} /></button>
              </div>
            ) : (
              <button onClick={() => setOnboarding(true)} className="ml-1 flex items-center gap-1.5 rounded-lg bg-gold px-3 py-2 text-sm font-semibold text-white hover:bg-gold-dark">
                <Compass size={16} /> Créer mon espace
              </button>
            )}
            <div className="ml-2"><AiStatus status={status} /></div>
          </nav>
        </div>
      </header>

      <main className={clsx('flex-1', pathname !== '/' && 'mx-auto w-full max-w-7xl px-4 py-8')}>
        <Routes>
          <Route path="/" element={<Home onStart={() => setOnboarding(true)} />} />
          <Route path="/entreprise" element={<Entreprise />} />
          <Route path="/administration/*" element={<Administration />} />
          <Route path="/plateforme" element={<AdminPlateforme />} />
        </Routes>
      </main>

      <footer className="bg-navy-950 text-slate-300">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-4">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2">
              <div className="rounded-xl bg-white p-1"><img src="/logo-icon.png" alt="" className="h-9 w-9" /></div>
              <div className="font-display text-lg font-bold text-white">J<span className="text-gold">i</span>SER <span className="font-sans font-normal text-gold">جسر</span></div>
            </div>
            <p className="mt-3 max-w-md text-sm">Le pont entre le contribuable et l'administration fiscale. IA · Conseil · Solution.</p>
            <p className="mt-3 text-xs text-slate-400">L'IA recommande et explique, un humain décide toujours.</p>
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Espaces</div>
            <ul className="mt-2 space-y-1.5 text-sm">
              <li><Link to="/entreprise" className="hover:text-gold">Entreprise et conseil</Link></li>
              <li><Link to="/administration" className="hover:text-gold">Administration fiscale</Link></li>
              <li><Link to="/plateforme" className="hover:text-gold">Admin plateforme</Link></li>
            </ul>
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Sources</div>
            <ul className="mt-2 space-y-1.5 text-sm">
              <li>CDPF, Code TVA, Code IRPP/IS</li>
              <li>Textes : Jurisite Tunisie</li>
              <li>Données de démonstration synthétiques</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 py-4 text-center text-xs text-slate-500">
          Prototype · Hackathon national IA &amp; Finances publiques · 2026
        </div>
      </footer>

      {onboarding && <Onboarding onClose={(s) => { setOnboarding(false); if (s) { saveSession(s); setSession(s) } }} />}
    </div>
  )
}
