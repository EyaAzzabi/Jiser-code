import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Clock, FileCheck2, Hourglass, LogOut, MailCheck, ShieldCheck, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi, comptesApi, espaceDuRole, frDate, ROLE_LABELS, saveSession, type Controle, type Piece, type Session, type Utilisateur } from '../api'
import { Button } from './ui'
import { asset } from '../apiBase'

type Statut = Utilisateur & { pieces: Piece[]; controles: Controle[]; delai_heures: number }

/** Shown to an account awaiting verification (or refused): nothing else is reachable until it is validated. */
export default function CompteEnAttente({ session }: { session: Session }) {
  const navigate = useNavigate()
  const [s, setS] = useState<Statut | null>(null)

  useEffect(() => {
    let stop = false
    const tick = () => comptesApi.statut().then((r) => {
      if (stop) return
      setS(r)
      if (r.statut === 'actif') {   // validated: refresh the session and open the space
        saveSession({ ...session, role: r.role, utilisateur: r })
        navigate(espaceDuRole(r.role))
      }
    }).catch(() => {})
    tick()
    const t = setInterval(tick, 20_000)
    return () => { stop = true; clearInterval(t) }
  }, [session, navigate])

  const logout = async () => {
    try { await authApi.deconnexion() } catch { /* already gone */ }
    saveSession(null)
    navigate('/')
  }
  const u = s ?? session.utilisateur
  const refuse = u?.statut === 'refuse'
  const soumis = u?.verification?.soumis_le
  const heures = soumis ? Math.max(0, (Date.now() - new Date(soumis).getTime()) / 3600000) : 0
  const reste = Math.max(0, 24 - heures)

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-2xl rounded-3xl bg-white p-8 shadow-xl">
        <div className="flex items-center justify-between">
          <img src={asset('logo.png')} alt="JISER" className="w-28" />
          <button onClick={logout} className="flex items-center gap-1 text-sm text-slate-500 hover:text-rose-700"><LogOut size={16} /> Se déconnecter</button>
        </div>
        <div className={clsx('mt-6 flex items-start gap-4 rounded-2xl p-5', refuse ? 'bg-rose-50' : 'bg-gold-light/60')}>
          <div className={clsx('rounded-2xl p-3', refuse ? 'bg-rose-600 text-white' : 'bg-gold text-white')}>{refuse ? <XCircle size={28} /> : <Hourglass size={28} />}</div>
          <div>
            <h1 className="text-2xl font-bold text-navy-900">{refuse ? 'Demande non acceptée' : 'Vérification de votre compte en cours'}</h1>
            <p className="mt-1 text-slate-600">
              {refuse
                ? <>Motif : <b>{u?.verification?.motif || 'non précisé'}</b>. Répondez à l'e-mail reçu pour compléter votre dossier.</>
                : <>Bonjour {u?.prenom}, votre demande d'accès en tant que <b>{ROLE_LABELS[u?.role ?? ''] ?? u?.role}</b> est entre les mains de notre équipe.
                  Réponse sous 24 heures{soumis ? <> (encore environ <b>{Math.ceil(reste)} h</b>)</> : null}. Vous recevrez un e-mail de confirmation.</>}
            </p>
          </div>
        </div>

        {!refuse && (
          <ol className="mt-6 grid gap-3 sm:grid-cols-4">
            {[
              { ok: true, icon: MailCheck, t: 'E-mail vérifié' },
              { ok: true, icon: FileCheck2, t: 'Justificatifs reçus' },
              { ok: false, icon: ShieldCheck, t: 'Validation humaine' },
              { ok: false, icon: CheckCircle2, t: 'Accès ouvert' },
            ].map(({ ok, icon: Icon, t }, i) => (
              <li key={t} className={clsx('rounded-2xl p-3 text-center text-sm', ok ? 'bg-emerald-50 text-emerald-800' : i === 2 ? 'bg-gold-light/60 text-navy-900' : 'bg-canvas text-slate-500')}>
                <Icon size={20} className="mx-auto mb-1" />{t}
              </li>
            ))}
          </ol>
        )}

        {s && s.controles.length > 0 && (
          <div className="mt-6">
            <div className="text-sm font-semibold text-navy-900">Pré-vérification automatique</div>
            <ul className="mt-2 divide-y divide-slate-100 rounded-2xl border border-slate-200">
              {s.controles.map((c) => (
                <li key={c.controle} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  {c.statut === 'ok' ? <CheckCircle2 size={16} className="text-emerald-600" /> : c.statut === 'alerte' ? <AlertTriangle size={16} className="text-amber-500" /> : <XCircle size={16} className="text-rose-600" />}
                  <span className="flex-1 text-slate-700">{c.controle}</span>
                  <span className="text-xs text-slate-500">{c.detail}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-slate-500">Les points signalés sont examinés par le validateur : ils n'entraînent pas un refus automatique.</p>
          </div>
        )}
        {s && (
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Clock size={14} /> Demande envoyée le {frDate(soumis ?? null)} · {s.pieces.length} justificatif(s) chiffré(s)
          </div>
        )}
        <div className="mt-6 flex justify-end"><Button variant="light" onClick={() => navigate('/')}>Retour à l'accueil</Button></div>
      </div>
    </div>
  )
}
