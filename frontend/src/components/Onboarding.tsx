import clsx from 'clsx'
import { ArrowLeft, ArrowRight, BadgeCheck, Check, CheckCircle2, Clock, FileCheck2, FileSearch, FileUp, Gavel, Lock, MailCheck, Scale, ShieldCheck, UserCheck, X } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi, comptesApi, saveSession, type Session, type Utilisateur } from '../api'
import OtpCode from './OtpCode'
import { FAMILLES, roleConfig, ROLES, validateSection, type Famille, type Field, type Role } from './onboardingConfig'
import { Button } from './ui'

type Values = Record<string, unknown>

// ---- form controls -------------------------------------------------------------------------

function Label({ f, children, group }: { f: { label: string; required?: boolean; help?: string }; children: ReactNode; group?: boolean }) {
  const inner = (
    <>
      <span className="text-sm font-medium text-navy-900">{f.label}{f.required && <span className="text-gold"> *</span>}</span>
      <div className="mt-1">{children}</div>
      {f.help && <span className="mt-1 block text-xs text-slate-500">{f.help}</span>}
    </>
  )
  // a <label> would name only its first button: groups of choice buttons use role="group" instead
  return group ? <div role="group" aria-label={f.label} className="block">{inner}</div> : <label className="block">{inner}</label>
}

const inputCls = (error?: string) => clsx('w-full rounded-xl border bg-white px-3 py-2.5 text-sm outline-none transition focus:ring-2',
  error ? 'border-rose-300 focus:ring-rose-200' : 'border-slate-300 focus:border-gold focus:ring-gold/30')

function FieldInput({ f, value, error, onChange }: { f: Field; value: unknown; error?: string; onChange: (v: unknown) => void }) {
  let control: ReactNode
  if (f.type === 'select') {
    control = (
      <select value={String(value ?? '')} onChange={(e) => onChange(e.target.value)} className={inputCls(error)}>
        <option value="">Choisir…</option>
        {f.options!.map((o) => <option key={o}>{o}</option>)}
      </select>
    )
  } else if (f.type === 'multi') {
    const arr = (value as string[]) ?? []
    control = (
      <div className="flex flex-wrap gap-2">
        {f.options!.map((o) => {
          const on = arr.includes(o)
          return (
            <button key={o} type="button" onClick={() => onChange(on ? arr.filter((x) => x !== o) : [...arr, o])}
              className={clsx('rounded-full px-3 py-1.5 text-xs font-medium ring-1 transition', on ? 'bg-navy-900 text-white ring-navy-900' : 'bg-white text-slate-600 ring-slate-300 hover:ring-gold')}>
              {on && <Check size={12} className="mr-1 inline" />}{o}
            </button>
          )
        })}
      </div>
    )
  } else {
    control = (
      <input type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'} value={String(value ?? '')} placeholder={f.placeholder}
        onChange={(e) => onChange(e.target.value)} className={inputCls(error)} />
    )
  }
  return (
    <div className={clsx(f.full && 'sm:col-span-2')}>
      <Label f={f} group={f.type === 'multi'}>{control}</Label>
      {error && <span className="mt-1 block text-xs font-medium text-rose-600">{error}</span>}
    </div>
  )
}

const TAILLE_MAX = 5 * 1024 * 1024
const ko = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} Mo` : `${Math.round(n / 1024)} Ko`)

// ---- Wizard --------------------------------------------------------------------------------

type StepId = 'bienvenue' | 'famille' | 'role' | 'identite' | 'otp' | `section-${number}` | 'justificatifs' | 'preferences' | 'recap' | 'envoye'
const LANGUES: Record<string, string> = { Français: 'fr', 'العربية': 'ar' }

export default function Onboarding({ onClose, onLogin }: { onClose: () => void; onLogin: () => void }) {
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState(0)
  const [famille, setFamille] = useState<Famille | null>(null)
  const [role, setRole] = useState<Role | null>(null)
  const [identite, setIdentite] = useState({ prenom: '', nom: '', fonction: '', email: '', telephone: '' })
  const [details, setDetails] = useState<Values>({})
  const [fichiers, setFichiers] = useState<Record<string, File>>({})
  const [prefs, setPrefs] = useState<Values>({ langue: 'Français', alertes: ['E-mail', "Dans l'application"] })
  const [consents, setConsents] = useState({ cgu: false, donnees_personnelles: false, analyse_ia: false, communications: false })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [verified, setVerified] = useState(false)
  const [busy, setBusy] = useState(false)
  const [apiError, setApiError] = useState('')
  const [envoye, setEnvoye] = useState<Utilisateur | null>(null)

  const cfg = roleConfig(role)
  const admin = famille === 'administration'
  const steps: StepId[] = useMemo(() => [
    'bienvenue', 'famille', ...(admin ? ['role' as StepId] : []), 'identite', 'otp',
    ...(cfg?.sections.map((_, i) => `section-${i}` as StepId) ?? []),
    'justificatifs', 'preferences', 'recap', 'envoye',
  ], [cfg, admin])
  const step = steps[stepIndex]
  const rail = [
    { id: 'famille', label: 'Profil' }, ...(admin ? [{ id: 'role', label: 'Rôle et droits' }] : []),
    { id: 'identite', label: 'Identité' }, { id: 'otp', label: 'Vérification e-mail' },
    ...(cfg?.sections.map((s, i) => ({ id: `section-${i}`, label: s.title })) ?? [{ id: 'section-0', label: 'Informations métier' }]),
    { id: 'justificatifs', label: 'Justificatifs' }, { id: 'preferences', label: 'Consentements' }, { id: 'recap', label: 'Récapitulatif' },
  ]
  const railIndex = step === 'envoye' ? rail.length : rail.findIndex((r) => r.id === step)

  const close = () => {
    if (verified && !envoye) saveSession(null)   // an unfinished signup must not leave a half-open session
    onClose()
  }

  const validate = (): boolean => {
    let errs: Record<string, string> = {}
    if (step === 'identite') {
      if (!identite.prenom.trim()) errs.prenom = 'Champ obligatoire'
      if (!identite.nom.trim()) errs.nom = 'Champ obligatoire'
      if (!/^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/.test(identite.email.trim())) errs.email = 'Adresse e-mail invalide'
      if (identite.telephone.trim() && !/^(\+216)?\s?[2-9]\d(\s?\d{3}){2}$/.test(identite.telephone.replace(/[.-]/g, ' ').trim()))
        errs.telephone = 'Numéro tunisien : 8 chiffres (ex. 22 123 456)'
    } else if (step.startsWith('section-') && cfg) {
      errs = validateSection(cfg.sections[Number(step.split('-')[1])], details)
    } else if (step === 'justificatifs' && cfg) {
      for (const p of cfg.pieces) if (!fichiers[p.type]) errs[p.type] = 'Pièce obligatoire'
    } else if (step === 'preferences') {
      if (!consents.cgu) errs.cgu = 'Obligatoire'
      if (!consents.donnees_personnelles) errs.donnees_personnelles = 'Obligatoire'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const next = () => {
    setApiError('')
    if (step === 'famille' && famille === 'entreprise') setRole('entreprise')
    if (!validate()) return
    if (step === 'identite' && verified) { setStepIndex(stepIndex + 2); return }   // e-mail already verified
    setStepIndex(Math.min(stepIndex + 1, steps.length - 1))
  }
  const back = () => {
    setErrors({}); setApiError('')
    const target = steps[stepIndex - 1] === 'otp' && verified ? stepIndex - 2 : stepIndex - 1
    setStepIndex(Math.max(target, 0))
  }

  const finish = async () => {
    if (!cfg) return
    setBusy(true); setApiError('')
    try {
      const r = await authApi.enregistrerProfil({
        role, nom: identite.nom.trim(), prenom: identite.prenom.trim(), fonction: identite.fonction.trim(),
        langue: LANGUES[String(prefs.langue)] ?? 'fr',
        details: { ...details, telephone: identite.telephone, preferences: prefs }, consentements: consents,
      })
      for (const p of cfg.pieces) await comptesApi.deposerPiece(p.type, fichiers[p.type])
      const u = await comptesApi.soumettre()
      const token = (JSON.parse(sessionStorage.getItem('jiser-session') ?? '{}') as Session).token
      saveSession({ token, role: r.utilisateur.role, utilisateur: u })
      setEnvoye(u)
      setStepIndex(steps.indexOf('envoye'))
    } catch (e) { setApiError((e as Error).message) } finally { setBusy(false) }
  }

  const deadline = (() => {
    const d = details.date_notification as string | undefined
    if (!d) return null
    const dt = new Date(d); dt.setDate(dt.getDate() + 45)
    const left = Math.ceil((dt.getTime() - Date.now()) / 86400000)
    return { date: dt.toLocaleDateString('fr-FR'), left }
  })()
  const adminRoles = ROLES.filter((r) => r.famille === 'administration')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 p-3 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Créer votre espace JISER">
      <div className="animate-fade-up relative flex max-h-[94vh] w-full max-w-5xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        {step !== 'bienvenue' && (
          <aside className="hidden w-64 shrink-0 bg-gradient-to-b from-navy-900 to-navy-700 p-6 text-white md:block">
            <img src="/logo-icon.png" alt="" className="h-12 w-12 rounded-xl bg-white p-1" />
            <div className="mt-3 font-display text-lg font-bold">Demande d'accès</div>
            {cfg && <div className="text-xs text-gold">{cfg.label}</div>}
            <ol className="mt-6 space-y-1">
              {rail.map((r, i) => {
                const done = i < railIndex
                const active = i === railIndex
                return (
                  <li key={r.id} className={clsx('flex items-center gap-3 rounded-lg px-2 py-2 text-sm', active && 'bg-white/10')}>
                    <span className={clsx('flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                      done ? 'bg-gold text-white' : active ? 'bg-white text-navy-900' : 'bg-white/15 text-slate-300')}>
                      {done ? <Check size={14} /> : i + 1}
                    </span>
                    <span className={clsx(active ? 'font-semibold text-white' : done ? 'text-slate-200' : 'text-slate-400')}>{r.label}</span>
                  </li>
                )
              })}
            </ol>
            <div className="mt-8 rounded-xl bg-white/10 p-3 text-xs text-slate-200">
              <Lock size={14} className="mb-1 text-gold" />
              Vos données et justificatifs sont chiffrés (loi organique 2004-63) et ne servent qu'à vérifier votre identité et traiter vos dossiers.
            </div>
          </aside>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <button onClick={close} aria-label="Fermer" className="absolute right-4 top-4 z-10 rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-navy-900"><X size={20} /></button>
          <div className="flex-1 overflow-y-auto p-8">

            {step === 'bienvenue' && (
              <div className="py-4 text-center">
                <img src="/logo.png" alt="JISER" className="mx-auto w-48" />
                <h2 className="mt-4 text-3xl font-bold text-navy-900">Bienvenue sur JISER</h2>
                <p className="mx-auto mt-2 max-w-lg text-slate-600">Le pont entre le contribuable et l'administration fiscale. Chaque compte est vérifié avant d'être activé.</p>
                <div className="mx-auto mt-8 grid max-w-3xl gap-3 text-left sm:grid-cols-3">
                  {[
                    { icon: FileSearch, t: 'Comprendre', d: 'La notification expliquée chef par chef, en français ou en arabe.' },
                    { icon: Scale, t: 'Vérifier', d: 'La procédure contrôlée article par article (CDPF).' },
                    { icon: Gavel, t: 'Résoudre', d: 'Échange sécurisé avec l\'administration, réponse ou conciliation.' },
                  ].map(({ icon: Icon, t, d }) => (
                    <div key={t} className="rounded-2xl bg-canvas p-4">
                      <Icon className="text-gold" size={22} />
                      <div className="mt-2 font-semibold text-navy-900">{t}</div>
                      <div className="text-sm text-slate-600">{d}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {step === 'famille' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Qui êtes-vous ?</h2>
                <p className="mt-1 text-slate-600">Votre espace, vos étapes et vos droits d'accès dépendent de votre profil. Chaque espace est cloisonné.</p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {FAMILLES.map(({ id, label, who, icon: Icon }) => (
                    <button key={id} onClick={() => { setFamille(id); setRole(id === 'entreprise' ? 'entreprise' : null); setDetails({}); setFichiers({}) }}
                      className={clsx('flex items-start gap-3 rounded-2xl p-5 text-left ring-2 transition',
                        famille === id ? 'bg-gold-light/60 ring-gold' : 'bg-white ring-slate-200 hover:ring-bridge')}>
                      <div className={clsx('rounded-xl p-2.5', famille === id ? 'bg-gold text-white' : 'bg-bridge-light text-navy-800')}><Icon size={22} /></div>
                      <div><div className="font-semibold text-navy-900">{label}</div><div className="text-sm text-slate-500">{who}</div></div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 'role' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Votre rôle dans l'administration</h2>
                <p className="mt-1 text-slate-600">JISER respecte la hiérarchie de l'administration fiscale : chaque rôle a ses droits et ses privilèges.</p>
                <div className="relative mt-6 space-y-3">
                  <div className="absolute bottom-8 left-[27px] top-8 w-0.5 bg-gradient-to-b from-gold via-bridge to-navy-700" aria-hidden />
                  {adminRoles.map(({ id, label, who, niveau, droits, icon: Icon }) => (
                    <button key={id} onClick={() => { setRole(id); setDetails({}); setFichiers({}) }}
                      className={clsx('relative flex w-full items-start gap-4 rounded-2xl p-4 text-left ring-2 transition',
                        role === id ? 'bg-gold-light/60 ring-gold' : 'bg-white ring-slate-200 hover:ring-bridge')}>
                      <div className={clsx('z-10 rounded-xl p-2.5', role === id ? 'bg-gold text-white' : 'bg-navy-900 text-gold')}><Icon size={22} /></div>
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-navy-900">{label}</span>
                          <span className="rounded-full bg-canvas px-2 py-0.5 text-[11px] font-medium text-slate-500">{niveau}</span></div>
                        <div className="text-sm text-slate-500">{who}</div>
                        <ul className="mt-2 grid gap-1 text-xs text-slate-600 sm:grid-cols-3">
                          {droits?.map((d) => <li key={d} className="flex gap-1"><Check size={12} className="mt-0.5 shrink-0 text-gold" />{d}</li>)}
                        </ul>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 'identite' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Votre identité</h2>
                <p className="mt-1 text-slate-600">Un code de vérification sera envoyé à votre adresse e-mail.</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  {([['prenom', 'Prénom', 'Sami', true], ['nom', 'Nom', 'Ben Salah', true],
                    ['fonction', 'Fonction', cfg?.id === 'entreprise' ? 'Gérant' : cfg?.label ?? '', false],
                    ['email', admin ? 'E-mail professionnel (adresse officielle de l\'administration)' : 'E-mail professionnel', admin ? 'prenom.nom@finances.gov.tn' : 'sami@elamen.tn', true],
                    ['telephone', 'Téléphone mobile', '22 123 456', false]] as const).map(([k, label, ph, req]) => (
                    <div key={k} className={clsx(k === 'email' && 'sm:col-span-2')}>
                      <Label f={{ label, required: req, help: k === 'email' && admin ? 'Une adresse non officielle est signalée au validateur et peut entraîner un refus.' : undefined }}>
                        <input value={identite[k]} placeholder={ph} type={k === 'email' ? 'email' : k === 'telephone' ? 'tel' : 'text'}
                          onChange={(e) => {
                            setIdentite({ ...identite, [k]: e.target.value })
                            if (k === 'email' && verified) { setVerified(false); saveSession(null) }   // a new address must be verified again
                          }}
                          className={inputCls(errors[k])} />
                      </Label>
                      {errors[k] && <span className="mt-1 block text-xs font-medium text-rose-600">{errors[k]}</span>}
                    </div>
                  ))}
                </div>
                <p className="mt-6 text-sm text-slate-500">Déjà inscrit ? <button onClick={() => { close(); onLogin() }} className="font-medium text-navy-900 underline decoration-gold underline-offset-4">Se connecter</button></p>
              </div>
            )}

            {step === 'otp' && (
              <OtpCode email={identite.email.trim()} intention="inscription" onVerified={(r) => {
                saveSession({ token: r.token, role: null, utilisateur: null })
                setVerified(true)
                setStepIndex(stepIndex + 1)
              }} />
            )}

            {step.startsWith('section-') && cfg && (() => {
              const section = cfg.sections[Number(step.split('-')[1])]
              return (
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-gold"><BadgeCheck size={14} /> E-mail vérifié · {cfg.label}</div>
                  <h2 className="mt-1 text-2xl font-bold text-navy-900">{section.title}</h2>
                  <p className="mt-1 text-slate-600">{section.subtitle}</p>
                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    {section.fields.filter((f) => !f.showIf || f.showIf(details)).map((f) => (
                      <FieldInput key={f.key} f={f} value={details[f.key]} error={errors[f.key]}
                        onChange={(v) => setDetails({ ...details, [f.key]: v })} />
                    ))}
                  </div>
                </div>
              )
            })()}

            {step === 'justificatifs' && cfg && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Vos justificatifs</h2>
                <p className="mt-1 text-slate-600">Ils permettent de vérifier votre identité avant d'ouvrir votre accès. Ils sont chiffrés et ne sont vus que par {cfg.validateur}.</p>
                <div className="mt-6 space-y-3">
                  {cfg.pieces.map((p) => {
                    const f = fichiers[p.type]
                    return (
                      <label key={p.type} className={clsx('flex cursor-pointer items-center gap-4 rounded-2xl border-2 border-dashed p-4 transition',
                        errors[p.type] ? 'border-rose-300 bg-rose-50' : f ? 'border-emerald-300 bg-emerald-50/50' : 'border-slate-300 hover:border-gold hover:bg-canvas')}>
                        <div className={clsx('rounded-xl p-2.5', f ? 'bg-emerald-600 text-white' : 'bg-navy-900 text-gold')}>{f ? <FileCheck2 size={20} /> : <FileUp size={20} />}</div>
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-navy-900">{p.label} <span className="text-gold">*</span></div>
                          <div className="truncate text-sm text-slate-500">{f ? `${f.name} · ${ko(f.size)}` : p.help}</div>
                          {errors[p.type] && <div className="text-xs font-medium text-rose-600">{errors[p.type]}</div>}
                        </div>
                        <span className="text-sm font-medium text-navy-900 underline decoration-gold underline-offset-4">{f ? 'Changer' : 'Choisir un fichier'}</span>
                        <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (!file) return
                          if (file.size > TAILLE_MAX) { setErrors({ ...errors, [p.type]: 'Fichier trop volumineux (5 Mo maximum)' }); return }
                          setErrors({ ...errors, [p.type]: '' }); setFichiers({ ...fichiers, [p.type]: file })
                        }} />
                      </label>
                    )
                  })}
                </div>
                <div className="mt-4 flex items-start gap-2 rounded-xl bg-canvas p-3 text-xs text-slate-600">
                  <ShieldCheck size={16} className="shrink-0 text-gold" />
                  JISER vérifie automatiquement la cohérence de vos pièces avec votre saisie (matricule, raison sociale). Les images ne sont jamais envoyées à une IA externe.
                </div>
              </div>
            )}

            {step === 'preferences' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Préférences et consentements</h2>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <FieldInput f={{ key: 'langue', label: 'Langue des explications et de l\'assistant', type: 'select', options: Object.keys(LANGUES),
                    help: 'Le brouillon de réponse officiel reste rédigé en français.' }}
                    value={prefs.langue} onChange={(v) => setPrefs({ ...prefs, langue: v })} />
                  <FieldInput f={{ key: 'alertes', label: 'Recevoir les alertes par', type: 'multi', options: ['E-mail', "Dans l'application"] }}
                    value={prefs.alertes} onChange={(v) => setPrefs({ ...prefs, alertes: v })} />
                </div>
                <div className="mt-6 space-y-3">
                  {([
                    ['cgu', "J'accepte les conditions générales d'utilisation de JISER.", true],
                    ['donnees_personnelles', "J'accepte le traitement de mes données pour le traitement de mes dossiers, conformément à la loi organique n° 2004-63 (INPDP). Je peux exporter ou supprimer mes données à tout moment.", true],
                    ['analyse_ia', "J'accepte que des textes pseudonymisés (sans nom, matricule ni coordonnées) soient traités par une IA générative pour m'expliquer mes dossiers. Sans ce consentement, JISER fonctionne avec ses règles et son modèle interne.", false],
                    ['communications', "J'accepte de recevoir des informations sur les nouveautés fiscales (facultatif).", false],
                  ] as const).map(([k, text, req]) => (
                    <label key={k} className={clsx('flex cursor-pointer gap-3 rounded-xl border p-3 text-sm', errors[k] ? 'border-rose-300 bg-rose-50' : 'border-slate-200 hover:bg-canvas')}>
                      <input type="checkbox" checked={consents[k]} onChange={(e) => setConsents({ ...consents, [k]: e.target.checked })} className="mt-0.5 h-4 w-4 accent-[#c29a2e]" />
                      <span className="text-slate-700">{text}{req && <span className="text-gold"> *</span>}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {step === 'recap' && cfg && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Vérifiez votre demande, {identite.prenom}</h2>
                <p className="mt-1 text-slate-600">Votre demande sera vérifiée par {cfg.validateur} sous 24 heures. Vous recevrez un e-mail de confirmation.</p>
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 p-4 text-sm">
                    <div className="font-semibold text-navy-900">{identite.prenom} {identite.nom}</div>
                    <div className="text-slate-500">{cfg.label}{identite.fonction ? ` · ${identite.fonction}` : ''}</div>
                    <div className="mt-2 flex items-center gap-1.5 text-emerald-700"><ShieldCheck size={14} /> {identite.email} vérifié</div>
                    <div className="mt-1 text-slate-500">Justificatifs : {cfg.pieces.map((p) => fichiers[p.type]?.name).filter(Boolean).join(', ')}</div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 p-4 text-sm">
                    {cfg.sections.flatMap((s) => s.fields).filter((f) => details[f.key] !== undefined && details[f.key] !== '').slice(0, 6).map((f) => (
                      <div key={f.key} className="flex justify-between gap-3 py-0.5"><span className="text-slate-500">{f.label}</span><span className="text-right font-medium text-navy-900">{Array.isArray(details[f.key]) ? (details[f.key] as string[]).join(', ') : String(details[f.key])}</span></div>
                    ))}
                  </div>
                </div>
                {deadline && (
                  <div className={clsx('mt-4 rounded-2xl p-4 text-sm', deadline.left <= 7 ? 'bg-rose-50 text-rose-700' : 'bg-gold-light/60 text-navy-900')}>
                    ⏰ Date limite pour répondre à votre notification : <b>{deadline.date}</b> ({deadline.left >= 0 ? `il reste ${deadline.left} jours` : 'délai dépassé'} ; art. 44 du CDPF).
                  </div>
                )}
                <div className="mt-6 text-sm font-semibold text-navy-900">Votre parcours une fois l'accès validé</div>
                <ol className="mt-2 grid gap-3 md:grid-cols-3">
                  {cfg.parcours.map((s, i) => (
                    <li key={s} className="flex items-start gap-3 rounded-2xl bg-canvas p-4 text-sm">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy-900 font-bold text-white">{i + 1}</span>
                      <span className="text-slate-700">{s}</span>
                    </li>
                  ))}
                </ol>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="flex items-center gap-1"><UserCheck size={14} className="text-gold" /> L'humain décide</span>·
                  <span className="flex items-center gap-1"><BadgeCheck size={14} className="text-gold" /> Articles cités</span>·
                  <span className="flex items-center gap-1"><ShieldCheck size={14} className="text-gold" /> Données chiffrées</span>
                </div>
              </div>
            )}

            {step === 'envoye' && cfg && envoye && (
              <div className="py-2 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600"><MailCheck size={32} /></div>
                <h2 className="mt-4 text-2xl font-bold text-navy-900">Demande envoyée</h2>
                <p className="mx-auto mt-2 max-w-lg text-slate-600">Vos informations sont en cours de vérification. Vous recevrez un e-mail de confirmation dès que votre espace sera activé, <b>sous 24 heures</b>.</p>
                <ol className="mx-auto mt-6 max-w-md space-y-3 text-left">
                  {[
                    { ok: true, t: 'Adresse e-mail vérifiée', d: 'Code à usage unique' },
                    { ok: true, t: 'Pré-vérification automatique', d: `${envoye.verification?.score ?? 0} % des contrôles conformes` },
                    { ok: false, t: 'Validation humaine', d: `Par ${cfg.validateur}` },
                    { ok: false, t: 'Accès à votre espace', d: 'E-mail de confirmation' },
                  ].map((s) => (
                    <li key={s.t} className="flex items-center gap-3 rounded-xl bg-canvas p-3">
                      {s.ok ? <CheckCircle2 className="text-emerald-600" size={20} /> : <Clock className="text-gold-dark" size={20} />}
                      <div><div className="text-sm font-semibold text-navy-900">{s.t}</div><div className="text-xs text-slate-500">{s.d}</div></div>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {apiError && <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{apiError}</div>}
          </div>

          <div className="flex items-center justify-between border-t border-slate-100 px-8 py-4">
            {step === 'bienvenue'
              ? <button onClick={() => { onClose(); onLogin() }} className="text-sm font-medium text-navy-900 hover:text-gold-dark">J'ai déjà un compte</button>
              : step === 'envoye' ? <span />
                : <Button variant="ghost" onClick={back} disabled={busy}><ArrowLeft size={16} /> Retour</Button>}
            {step === 'envoye'
              ? <Button variant="gold" onClick={() => { onClose(); navigate('/compte') }}>Suivre ma demande <ArrowRight size={16} /></Button>
              : step === 'recap'
                ? <Button variant="gold" onClick={finish} disabled={busy}>{busy ? 'Envoi sécurisé…' : 'Envoyer ma demande'} <ArrowRight size={16} /></Button>
                : step === 'otp' ? <span className="text-xs text-slate-400">Étape sécurisée</span>
                  : <Button variant={step === 'bienvenue' ? 'gold' : 'primary'} onClick={next}
                    disabled={(step === 'famille' && !famille) || (step === 'role' && !role)}>
                    {step === 'bienvenue' ? 'Commencer' : step === 'famille' && !famille ? 'Choisissez un profil' : step === 'role' && !role ? 'Choisissez un rôle'
                      : step === 'identite' && !verified ? 'Recevoir mon code' : 'Continuer'} <ArrowRight size={16} />
                  </Button>}
          </div>
        </div>
      </div>
    </div>
  )
}
