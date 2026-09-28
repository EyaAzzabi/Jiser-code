import { ArrowRight, Lock, ShieldCheck, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { espaceDuRole, saveSession, type Role, type Session } from '../api'
import OtpCode from './OtpCode'
import { Button } from './ui'
import { asset } from '../apiBase'

/** E-mail + OTP sign-in form. `intention="admin"` is the private platform-administrator entrance. */
export function LoginForm({ intention, onDone, footer }: { intention: 'connexion' | 'admin'; onDone: (s: Session) => void; footer?: ReactNode }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const valid = /^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/.test(email.trim())

  if (sent) {
    return (
      <div>
        <OtpCode email={email.trim()} intention={intention} onVerified={(r) => {
          const s: Session = { token: r.token, role: r.role, utilisateur: r.utilisateur }
          saveSession(s)
          onDone(s)
        }} />
        <button onClick={() => setSent(false)} className="mx-auto mt-2 block text-sm text-slate-500 hover:text-navy-900">Changer d'adresse</button>
      </div>
    )
  }
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (valid) { setError(''); setSent(true) } else setError('Adresse e-mail invalide') }}>
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-900 text-gold">
        {intention === 'admin' ? <Lock size={28} /> : <ShieldCheck size={28} />}
      </div>
      <h2 className="mt-4 text-center text-2xl font-bold text-navy-900">{intention === 'admin' ? 'Administration de la plateforme' : 'Connexion à votre espace'}</h2>
      <p className="mt-1 text-center text-slate-600">{intention === 'admin' ? 'Accès réservé aux administrateurs autorisés.' : 'Un code de vérification vous sera envoyé par e-mail.'}</p>
      <label className="mt-6 block">
        <span className="text-sm font-medium text-navy-900">Adresse e-mail</span>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus placeholder="vous@exemple.tn"
          className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-3 text-sm outline-none focus:border-gold focus:ring-2 focus:ring-gold/30" />
      </label>
      {error && <p className="mt-1 text-xs font-medium text-rose-600">{error}</p>}
      <Button type="submit" className="mt-5 w-full" variant="gold">Recevoir mon code <ArrowRight size={16} /></Button>
      {footer}
    </form>
  )
}

export default function LoginModal({ onClose, onSignup }: { onClose: () => void; onSignup: () => void }) {
  const navigate = useNavigate()
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 p-3 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Connexion">
      <div className="animate-fade-up relative w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl">
        <button onClick={onClose} aria-label="Fermer" className="absolute right-4 top-4 rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-navy-900"><X size={20} /></button>
        <LoginForm intention="connexion" onDone={(s) => { onClose(); navigate(espaceDuRole(s.role)) }}
          footer={<p className="mt-4 text-center text-sm text-slate-500">Pas encore de compte ? <button type="button" onClick={() => { onClose(); onSignup() }} className="font-medium text-navy-900 underline decoration-gold underline-offset-4">Créer mon espace</button></p>} />
      </div>
    </div>
  )
}

/** Shown instead of a private space when the visitor is not signed in with an allowed role. */
export function AccessGate({ session, roles, onLogin, onSignup }: { session: Session | null; roles: Role[]; onLogin: () => void; onSignup: () => void }) {
  const navigate = useNavigate()
  const wrongRole = session?.role && !roles.includes(session.role)
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 text-center shadow-xl">
        <img src={asset('logo.png')} alt="JISER" className="mx-auto w-36" />
        <h2 className="mt-4 text-2xl font-bold text-navy-900">{wrongRole ? 'Espace non autorisé' : 'Espace sécurisé'}</h2>
        <p className="mt-2 text-slate-600">{wrongRole ? "Votre profil n'a pas accès à cet espace." : 'Connectez-vous ou créez votre espace pour continuer.'}</p>
        <div className="mt-6 flex flex-col gap-2">
          {wrongRole ? (
            <Button onClick={() => navigate(espaceDuRole(session?.role))}>Aller à mon espace</Button>
          ) : (
            <>
              <Button variant="gold" onClick={onSignup}>Créer mon espace</Button>
              <Button variant="ghost" onClick={onLogin}>Se connecter</Button>
            </>
          )}
          <Button variant="light" onClick={() => navigate('/')}>Retour à l'accueil</Button>
        </div>
      </div>
    </div>
  )
}
