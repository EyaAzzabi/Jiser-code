import clsx from 'clsx'
import { ArrowLeft, ArrowRight, BadgeCheck, Check, FileSearch, Gavel, KeyRound, Lock, Mail, Scale, ShieldCheck, Smartphone, UserCheck, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi, type OtpDemande, type SessionInfo } from '../api'
import { roleConfig, ROLES, validateSection, type Field, type Role } from './onboardingConfig'
import { Button } from './ui'

export function shouldShowOnboarding(): boolean {
  try { return localStorage.getItem('jiser-onboarded') !== '1' } catch { return true }
}

type Values = Record<string, unknown>

// ---- small form controls -------------------------------------------------------------------

function Label({ f, children }: { f: { label: string; required?: boolean; help?: string }; children: ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-navy-900">{f.label}{f.required && <span className="text-gold"> *</span>}</span>
      <div className="mt-1">{children}</div>
      {f.help && <span className="mt-1 block text-xs text-slate-500">{f.help}</span>}
    </label>
  )
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
  } else if (f.type === 'toggle') {
    const on = value === undefined ? true : Boolean(value)
    control = (
      <button type="button" onClick={() => onChange(!on)} className="flex items-center gap-3">
        <span className={clsx('relative h-6 w-11 rounded-full transition', on ? 'bg-gold' : 'bg-slate-300')}>
          <span className={clsx('absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition', on ? 'left-5' : 'left-0.5')} />
        </span>
        <span className="text-sm text-slate-600">{on ? 'Activé' : 'Désactivé'}</span>
      </button>
    )
  } else {
    control = (
      <input type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'} value={String(value ?? '')} placeholder={f.placeholder}
        onChange={(e) => onChange(e.target.value)} className={inputCls(error)} />
    )
  }
  return (
    <div className={clsx(f.full && 'sm:col-span-2')}>
      <Label f={f}>{control}</Label>
      {error && <span className="mt-1 block text-xs font-medium text-rose-600">{error}</span>}
    </div>
  )
}

// ---- OTP -----------------------------------------------------------------------------------

function OtpBoxes({ value, onChange, disabled }: { value: string; onChange: (v: string) => void; disabled?: boolean }) {
  const refs = useRef<(HTMLInputElement | null)[]>([])
  const digits = value.padEnd(6, ' ').slice(0, 6).split('')
  const set = (i: number, d: string) => {
    const next = digits.map((x, j) => (j === i ? d : x)).join('').replace(/\s+$/, '')
    onChange(next.replace(/ /g, ''))
  }
  return (
    <div className="flex justify-center gap-2" onPaste={(e) => {
      const p = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
      if (p) { e.preventDefault(); onChange(p); refs.current[Math.min(p.length, 5)]?.focus() }
    }}>
      {digits.map((d, i) => (
        <input key={i} ref={(el) => { refs.current[i] = el }} inputMode="numeric" maxLength={1} disabled={disabled} aria-label={`Chiffre ${i + 1}`}
          value={d.trim()} autoFocus={i === 0}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(-1)
            set(i, v || ' ')
            if (v && i < 5) refs.current[i + 1]?.focus()
          }}
          onKeyDown={(e) => { if (e.key === 'Backspace' && !d.trim() && i > 0) refs.current[i - 1]?.focus() }}
          className="h-14 w-12 rounded-xl border border-slate-300 text-center font-display text-2xl font-bold text-navy-900 outline-none focus:border-gold focus:ring-2 focus:ring-gold/30" />
      ))}
    </div>
  )
}

// ---- Wizard --------------------------------------------------------------------------------

type StepId = 'bienvenue' | 'role' | 'identite' | 'otp' | `section-${number}` | 'preferences' | 'recap'

export default function Onboarding({ onClose }: { onClose: (session?: SessionInfo) => void }) {
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState(0)
  const [role, setRole] = useState<Role | null>(null)
  const [identite, setIdentite] = useState({ prenom: '', nom: '', fonction: '', email: '', telephone: '', canal: 'sms' as 'sms' | 'email' })
  const [details, setDetails] = useState<Values>({})
  const [prefs, setPrefs] = useState<Values>({ langue: 'Français', alertes: ['E-mail', "Dans l'application"] })
  const [consents, setConsents] = useState({ cgu: false, donnees_personnelles: false, analyse_ia: false, communications: false })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [otp, setOtp] = useState<OtpDemande | null>(null)
  const [code, setCode] = useState('')
  const [token, setToken] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [apiError, setApiError] = useState('')
  const [cooldown, setCooldown] = useState(0)

  const cfg = roleConfig(role)
  const steps: StepId[] = useMemo(() => [
    'bienvenue', 'role', 'identite', 'otp',
    ...(cfg?.sections.map((_, i) => `section-${i}` as StepId) ?? []),
    'preferences', 'recap',
  ], [cfg])
  const step = steps[stepIndex]
  const rail = [
    { id: 'role', label: 'Profil' }, { id: 'identite', label: 'Identité' }, { id: 'otp', label: 'Vérification OTP' },
    ...(cfg?.sections.map((s, i) => ({ id: `section-${i}`, label: s.title })) ?? [{ id: 'section-0', label: 'Informations métier' }]),
    { id: 'preferences', label: 'Préférences' }, { id: 'recap', label: 'Récapitulatif' },
  ]

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown(cooldown - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const destination = identite.canal === 'sms' ? identite.telephone : identite.email

  const sendOtp = async () => {
    setBusy(true); setApiError('')
    try {
      const r = await authApi.demanderOtp(identite.canal, destination)
      setOtp(r); setCode(''); setCooldown(r.renvoi_dans_s)
    } catch (e) { setApiError((e as Error).message) } finally { setBusy(false) }
  }

  const verifyOtp = async () => {
    setBusy(true); setApiError('')
    try {
      const r = await authApi.verifierOtp(identite.canal, destination, code)
      setToken(r.token)
      setStepIndex(stepIndex + 1)
    } catch (e) { setApiError((e as Error).message); setCode('') } finally { setBusy(false) }
  }

  const validate = (): boolean => {
    let errs: Record<string, string> = {}
    if (step === 'identite') {
      if (!identite.prenom.trim()) errs.prenom = 'Champ obligatoire'
      if (!identite.nom.trim()) errs.nom = 'Champ obligatoire'
      if (!/^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/.test(identite.email)) errs.email = 'Adresse e-mail invalide'
      if (!/^(\+216)?\s?[2-9]\d(\s?\d{3}){2}$/.test(identite.telephone.replace(/[.-]/g, ' ').trim())) errs.telephone = 'Numéro tunisien : 8 chiffres (ex. 22 123 456)'
    } else if (step.startsWith('section-') && cfg) {
      errs = validateSection(cfg.sections[Number(step.split('-')[1])], details)
    } else if (step === 'preferences') {
      if (!consents.cgu) errs.cgu = 'Obligatoire'
      if (!consents.donnees_personnelles) errs.donnees_personnelles = 'Obligatoire'
      if (!consents.analyse_ia) errs.analyse_ia = 'Obligatoire pour utiliser l\'analyse'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const next = () => {
    setApiError('')
    if (!validate()) return
    if (step === 'identite' && token) { setStepIndex(stepIndex + 2); return }   // contact already verified
    if (step === 'identite' && !otp) void sendOtp()
    setStepIndex(Math.min(stepIndex + 1, steps.length - 1))
  }
  const back = () => {
    setErrors({}); setApiError('')
    const target = steps[stepIndex - 1] === 'otp' && token ? stepIndex - 2 : stepIndex - 1
    setStepIndex(Math.max(target, 0))
  }

  const skip = () => {
    try { localStorage.setItem('jiser-onboarded', '1') } catch { /* ignore */ }
    onClose()
  }

  const finish = async () => {
    if (!token || !cfg) return
    setBusy(true); setApiError('')
    try {
      const r = await authApi.enregistrerProfil(token, {
        role, nom: identite.nom, prenom: identite.prenom, fonction: identite.fonction,
        langue: prefs.langue, details: { ...details, preferences: prefs }, consentements: consents,
      })
      try { localStorage.setItem('jiser-onboarded', '1'); localStorage.setItem('jiser-role', role!) } catch { /* ignore */ }
      onClose({ token, profil: r.profil })
      navigate(cfg.to)
    } catch (e) { setApiError((e as Error).message) } finally { setBusy(false) }
  }

  const deadline = (() => {
    const d = details.date_notification as string | undefined
    if (!d) return null
    const dt = new Date(d); dt.setDate(dt.getDate() + 30)
    const left = Math.ceil((dt.getTime() - Date.now()) / 86400000)
    return { date: dt.toLocaleDateString('fr-FR'), left }
  })()

  const railIndex = rail.findIndex((r) => r.id === step)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 p-3 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Créer votre espace JISER">
      <div className="animate-fade-up relative flex max-h-[94vh] w-full max-w-5xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        {/* Progress rail */}
        {step !== 'bienvenue' && (
          <aside className="hidden w-64 shrink-0 bg-gradient-to-b from-navy-900 to-navy-700 p-6 text-white md:block">
            <img src="/logo-icon.png" alt="" className="h-12 w-12 rounded-xl bg-white p-1" />
            <div className="mt-3 font-display text-lg font-bold">Créer votre espace</div>
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
              Vos données sont protégées (loi organique 2004-63) et ne servent qu'à traiter vos dossiers.
            </div>
          </aside>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <button onClick={skip} aria-label="Fermer" className="absolute right-4 top-4 z-10 rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-navy-900"><X size={20} /></button>
          <div className="flex-1 overflow-y-auto p-8">

            {step === 'bienvenue' && (
              <div className="py-4 text-center">
                <img src="/logo.png" alt="JISER" className="mx-auto w-48" />
                <h2 className="mt-4 text-3xl font-bold text-navy-900">Bienvenue sur JISER</h2>
                <p className="mx-auto mt-2 max-w-lg text-slate-600">Le pont entre le contribuable et l'administration fiscale. Créez votre espace sécurisé en quelques minutes.</p>
                <div className="mx-auto mt-8 grid max-w-3xl gap-3 text-left sm:grid-cols-3">
                  {[
                    { icon: FileSearch, t: 'Comprendre', d: 'La notification expliquée chef par chef, en langage simple.' },
                    { icon: Scale, t: 'Vérifier', d: 'La procédure contrôlée article par article (CDPF).' },
                    { icon: Gavel, t: 'Résoudre', d: 'Réponse argumentée ou conciliation, plus vite.' },
                  ].map(({ icon: Icon, t, d }) => (
                    <div key={t} className="rounded-2xl bg-canvas p-4">
                      <Icon className="text-gold" size={22} />
                      <div className="mt-2 font-semibold text-navy-900">{t}</div>
                      <div className="text-sm text-slate-600">{d}</div>
                    </div>
                  ))}
                </div>
                <div className="mx-auto mt-6 flex max-w-md items-center justify-center gap-2 rounded-xl bg-gold-light/70 px-4 py-2 text-sm text-navy-900">
                  <ShieldCheck size={16} className="text-gold-dark" /> Accès sécurisé par code à usage unique (OTP)
                </div>
              </div>
            )}

            {step === 'role' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Qui êtes-vous ?</h2>
                <p className="mt-1 text-slate-600">Votre espace, vos étapes et vos droits d'accès dépendent de votre profil.</p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {ROLES.map(({ id, label, who, icon: Icon }) => (
                    <button key={id} onClick={() => { setRole(id); setDetails({}) }}
                      className={clsx('flex items-start gap-3 rounded-2xl p-4 text-left ring-2 transition',
                        role === id ? 'bg-gold-light/60 ring-gold' : 'bg-white ring-slate-200 hover:ring-bridge')}>
                      <div className={clsx('rounded-xl p-2', role === id ? 'bg-gold text-white' : 'bg-bridge-light text-navy-800')}><Icon size={20} /></div>
                      <div><div className="font-semibold text-navy-900">{label}</div><div className="text-sm text-slate-500">{who}</div></div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 'identite' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Votre identité</h2>
                <p className="mt-1 text-slate-600">Nous vous enverrons un code à usage unique pour vérifier que c'est bien vous.</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  {([['prenom', 'Prénom', 'Sami'], ['nom', 'Nom', 'Ben Salah'], ['fonction', 'Fonction', cfg?.id === 'entreprise' ? 'Gérant' : 'Inspecteur'],
                    ['email', 'E-mail professionnel', 'sami@elamen.tn'], ['telephone', 'Téléphone mobile', '22 123 456']] as const).map(([k, label, ph]) => (
                    <div key={k}>
                      <Label f={{ label, required: k !== 'fonction' }}>
                        <input value={identite[k]} placeholder={ph} onChange={(e) => {
                            setIdentite({ ...identite, [k]: e.target.value })
                            // a new contact must be verified again
                            if (k === 'email' || k === 'telephone') { setOtp(null); setToken(null) }
                          }}
                          className={inputCls(errors[k])} type={k === 'email' ? 'email' : k === 'telephone' ? 'tel' : 'text'} />
                      </Label>
                      {errors[k] && <span className="mt-1 block text-xs font-medium text-rose-600">{errors[k]}</span>}
                    </div>
                  ))}
                  <div className="sm:col-span-2">
                    <span className="text-sm font-medium text-navy-900">Recevoir le code par</span>
                    <div className="mt-2 grid grid-cols-2 gap-3">
                      {([['sms', 'SMS', Smartphone], ['email', 'E-mail', Mail]] as const).map(([c, label, Icon]) => (
                        <button key={c} type="button" onClick={() => { setIdentite({ ...identite, canal: c }); setOtp(null); setToken(null) }}
                          className={clsx('flex items-center justify-center gap-2 rounded-xl p-3 text-sm font-medium ring-2',
                            identite.canal === c ? 'bg-gold-light/60 text-navy-900 ring-gold' : 'ring-slate-200 hover:ring-bridge')}>
                          <Icon size={16} /> {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {step === 'otp' && (
              <div className="mx-auto max-w-md py-4 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-900 text-gold"><KeyRound size={30} /></div>
                <h2 className="mt-4 text-2xl font-bold text-navy-900">Vérification de votre identité</h2>
                {otp ? (
                  <p className="mt-2 text-slate-600">Saisissez le code à 6 chiffres envoyé {identite.canal === 'sms' ? 'par SMS au' : 'par e-mail à'} <b>{otp.destination_masquee}</b>.</p>
                ) : <p className="mt-2 text-slate-600">Envoi du code en cours…</p>}
                {otp?.code_demo && (
                  <div className="mx-auto mt-4 rounded-xl border border-dashed border-gold bg-gold-light/50 p-3 text-sm text-navy-900">
                    <b>Mode démonstration</b> : aucun SMS n'est envoyé par le prototype. Votre code : <span className="font-display text-lg font-bold tracking-widest">{otp.code_demo}</span>
                  </div>
                )}
                <div className="mt-6"><OtpBoxes value={code} onChange={setCode} disabled={busy || !otp} /></div>
                <Button className="mt-6 w-full" onClick={verifyOtp} disabled={busy || code.length !== 6}>{busy ? 'Vérification…' : 'Vérifier le code'}</Button>
                <div className="mt-4 text-sm text-slate-500">
                  {cooldown > 0 ? <>Renvoyer un code dans <b>{cooldown} s</b></> : (
                    <button onClick={sendOtp} disabled={busy} className="font-medium text-navy-900 underline decoration-gold underline-offset-4">Renvoyer un code</button>
                  )}
                </div>
                <p className="mt-4 text-xs text-slate-400">Code valable 5 minutes · 5 tentatives maximum · usage unique</p>
              </div>
            )}

            {step.startsWith('section-') && cfg && (() => {
              const section = cfg.sections[Number(step.split('-')[1])]
              return (
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-gold"><BadgeCheck size={14} /> Identité vérifiée · {cfg.label}</div>
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

            {step === 'preferences' && (
              <div>
                <h2 className="text-2xl font-bold text-navy-900">Préférences et consentements</h2>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <FieldInput f={{ key: 'langue', label: 'Langue de l\'interface et des explications', type: 'select', options: ['Français', 'العربية', 'Tounsi (derja)'] }}
                    value={prefs.langue} onChange={(v) => setPrefs({ ...prefs, langue: v })} />
                  <FieldInput f={{ key: 'alertes', label: 'Recevoir les alertes (délais, décisions) par', type: 'multi', options: ['E-mail', 'SMS', "Dans l'application"] }}
                    value={prefs.alertes} onChange={(v) => setPrefs({ ...prefs, alertes: v })} />
                </div>
                <div className="mt-6 space-y-3">
                  {([
                    ['cgu', "J'accepte les conditions générales d'utilisation de JISER.", true],
                    ['donnees_personnelles', "J'accepte le traitement de mes données personnelles pour le traitement de mes dossiers, conformément à la loi organique n° 2004-63 (INPDP).", true],
                    ['analyse_ia', "J'ai compris que les analyses de l'IA sont des recommandations expliquées, et qu'une personne décide toujours.", true],
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
                <h2 className="text-2xl font-bold text-navy-900">Tout est prêt, {identite.prenom} !</h2>
                <p className="mt-1 text-slate-600">Vérifiez vos informations avant de créer votre espace.</p>
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 p-4 text-sm">
                    <div className="font-semibold text-navy-900">{identite.prenom} {identite.nom}</div>
                    <div className="text-slate-500">{identite.fonction || cfg.label}</div>
                    <div className="mt-2 flex items-center gap-1.5 text-emerald-700"><ShieldCheck size={14} /> {identite.canal === 'sms' ? identite.telephone : identite.email} vérifié par OTP</div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 p-4 text-sm">
                    {cfg.sections.flatMap((s) => s.fields).filter((f) => details[f.key] !== undefined && details[f.key] !== '' && f.type !== 'toggle').slice(0, 6).map((f) => (
                      <div key={f.key} className="flex justify-between gap-3 py-0.5"><span className="text-slate-500">{f.label}</span><span className="text-right font-medium text-navy-900">{Array.isArray(details[f.key]) ? (details[f.key] as string[]).join(', ') : String(details[f.key])}</span></div>
                    ))}
                  </div>
                </div>
                {deadline && (
                  <div className={clsx('mt-4 rounded-2xl p-4 text-sm', deadline.left <= 7 ? 'bg-rose-50 text-rose-700' : 'bg-gold-light/60 text-navy-900')}>
                    ⏰ Date limite pour répondre à votre notification : <b>{deadline.date}</b> ({deadline.left >= 0 ? `il reste ${deadline.left} jours` : 'délai dépassé'} ; art. 44 du CDPF).
                  </div>
                )}
                <div className="mt-6 text-sm font-semibold text-navy-900">Votre parcours</div>
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
                  <span className="flex items-center gap-1"><ShieldCheck size={14} className="text-gold" /> Journal de traçabilité</span>
                </div>
              </div>
            )}

            {apiError && <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{apiError}</div>}
          </div>

          <div className="flex items-center justify-between border-t border-slate-100 px-8 py-4">
            {step === 'bienvenue'
              ? <button onClick={skip} className="text-sm text-slate-500 hover:text-navy-900">Explorer sans compte</button>
              : <Button variant="ghost" onClick={back} disabled={busy || step === 'otp' && !!token}><ArrowLeft size={16} /> Retour</Button>}
            {step === 'recap'
              ? <Button variant="gold" onClick={finish} disabled={busy}>{busy ? 'Création…' : 'Créer mon espace'} <ArrowRight size={16} /></Button>
              : step === 'otp' ? <span className="text-xs text-slate-400">Étape sécurisée</span>
                : <Button variant={step === 'bienvenue' ? 'gold' : 'primary'} onClick={next} disabled={step === 'role' && !role}>
                  {step === 'bienvenue' ? 'Créer mon espace' : step === 'role' && !role ? 'Choisissez un profil' : step === 'identite' ? 'Recevoir mon code' : 'Continuer'} <ArrowRight size={16} />
                </Button>}
          </div>
        </div>
      </div>
    </div>
  )
}
