import { ArrowRight, LogOut } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { authApi, espaceDuRole, loadSession, onSessionChange, ROLES_ADMINISTRATION, saveSession, type Session } from './api'
import CompteEnAttente from './components/CompteEnAttente'
import LoginModal, { AccessGate } from './components/Login'
import Onboarding from './components/Onboarding'
import Administration from './pages/Administration'
import AdminPlateforme from './pages/AdminPlateforme'
import Entreprise from './pages/Entreprise'
import Home from './pages/Home'

function PublicHeader({ session, onLogin, onSignup }: { session: Session | null; onLogin: () => void; onSignup: () => void }) {
  const navigate = useNavigate()
  const logout = async () => {
    try { await authApi.deconnexion() } catch { /* already signed out */ }
    saveSession(null)
  }
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-2.5">
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/logo-icon.png" alt="Logo JISER" className="h-11 w-11" />
          <div className="leading-tight">
            <div className="font-display text-xl font-extrabold tracking-wide text-navy-900">J<span className="text-gold">i</span>SER <span className="font-sans font-normal text-gold">جسر</span></div>
            <div className="hidden text-[11px] text-slate-500 sm:block">Le pont entre le contribuable et l'administration fiscale</div>
          </div>
        </Link>
        <nav className="flex flex-wrap items-center gap-2">
          <a href="#solution" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 md:block">La solution</a>
          <a href="#pour-qui" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 md:block">Pour qui</a>
          {session?.role ? (
            <>
              <button onClick={() => navigate(espaceDuRole(session.role))} className="flex items-center gap-2 rounded-xl bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">
                Mon espace <ArrowRight size={14} />
              </button>
              <button onClick={logout} title="Se déconnecter" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><LogOut size={16} /></button>
            </>
          ) : (
            <>
              <button onClick={onLogin} className="rounded-xl px-4 py-2 text-sm font-semibold text-navy-900 ring-1 ring-slate-300 hover:bg-slate-50">Se connecter</button>
              <button onClick={onSignup} className="rounded-xl bg-gold px-4 py-2 text-sm font-semibold text-white hover:bg-gold-dark">Créer mon espace</button>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-navy-950 text-slate-300">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-3">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-white p-1"><img src="/logo-icon.png" alt="" className="h-9 w-9" /></div>
            <div className="font-display text-lg font-bold text-white">J<span className="text-gold">i</span>SER <span className="font-sans font-normal text-gold">جسر</span></div>
          </div>
          <p className="mt-3 max-w-md text-sm">Le pont entre le contribuable et l'administration fiscale. IA · Conseil · Solution.</p>
          <p className="mt-3 text-xs text-slate-400">L'IA recommande et explique, un humain décide toujours.</p>
        </div>
        <div>
          <div className="text-sm font-semibold text-white">Références</div>
          <ul className="mt-2 space-y-1.5 text-sm">
            <li>Code des droits et procédures fiscaux</li>
            <li>Code de la TVA · Code de l'IRPP et de l'IS</li>
            <li>Loi organique n° 2004-63 (données personnelles)</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 py-4 text-center text-xs text-slate-500">© 2026 JISER</div>
    </footer>
  )
}

export default function App() {
  const [session, setSession] = useState<Session | null>(loadSession())
  const [modal, setModal] = useState<'signup' | 'login' | null>(null)
  const { pathname } = useLocation()
  useEffect(() => onSessionChange(setSession), [])
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])

  const openLogin = () => setModal('login')
  const openSignup = () => setModal('signup')
  const complete = session?.role ? session : null   // a verified e-mail without a finished profile is not an account yet
  // an account waiting for verification (or refused) reaches nothing but its status page
  const enAttente = !!complete?.utilisateur?.statut && complete.utilisateur.statut !== 'actif'

  return (
    <>
      <Routes>
        <Route path="/" element={
          <div className="flex min-h-screen flex-col">
            <PublicHeader session={complete} onLogin={openLogin} onSignup={openSignup} />
            <main className="flex-1"><Home onSignup={openSignup} session={complete} /></main>
            <Footer />
          </div>
        } />
        <Route path="/compte" element={complete ? <CompteEnAttente session={complete} /> : <AccessGate session={null} roles={[]} onLogin={openLogin} onSignup={openSignup} />} />
        <Route path="/entreprise/*" element={complete && enAttente ? <CompteEnAttente session={complete} />
          : complete && complete.role === 'entreprise'
            ? <Entreprise session={complete} />
            : <AccessGate session={complete} roles={['entreprise']} onLogin={openLogin} onSignup={openSignup} />} />
        <Route path="/administration/*" element={complete && enAttente ? <CompteEnAttente session={complete} />
          : complete && ROLES_ADMINISTRATION.includes(complete.role!)
            ? <Administration session={complete} />
            : <AccessGate session={complete} roles={ROLES_ADMINISTRATION} onLogin={openLogin} onSignup={openSignup} />} />
        <Route path="/plateforme/*" element={<AdminPlateforme session={complete} />} />
        <Route path="*" element={<AccessGate session={complete} roles={[]} onLogin={openLogin} onSignup={openSignup} />} />
      </Routes>
      {modal === 'signup' && <Onboarding onClose={() => setModal(null)} onLogin={openLogin} />}
      {modal === 'login' && <LoginModal onClose={() => setModal(null)} onSignup={openSignup} />}
    </>
  )
}
