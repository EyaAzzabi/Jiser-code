import { KeyRound, MailCheck } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { authApi, type OtpDemande, type Role, type Utilisateur } from '../api'
import { Button } from './ui'

function OtpBoxes({ value, onChange, disabled }: { value: string; onChange: (v: string) => void; disabled?: boolean }) {
  const refs = useRef<(HTMLInputElement | null)[]>([])
  const digits = Array.from({ length: 6 }, (_, i) => value[i] ?? '')
  const setAt = (i: number, d: string) => {
    const next = [...digits]
    next[i] = d
    onChange(next.join('').slice(0, 6))
  }
  return (
    <div className="flex justify-center gap-2" onPaste={(e) => {
      const p = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
      if (p) { e.preventDefault(); onChange(p); refs.current[Math.min(p.length, 5)]?.focus() }
    }}>
      {digits.map((d, i) => (
        <input key={i} ref={(el) => { refs.current[i] = el }} inputMode="numeric" autoComplete={i === 0 ? 'one-time-code' : 'off'}
          maxLength={1} disabled={disabled} aria-label={`Chiffre ${i + 1}`} value={d} autoFocus={i === 0}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(-1)
            setAt(i, v)
            if (v && i < 5) refs.current[i + 1]?.focus()
          }}
          onKeyDown={(e) => { if (e.key === 'Backspace' && !d && i > 0) refs.current[i - 1]?.focus() }}
          className="h-14 w-12 rounded-xl border border-slate-300 text-center font-display text-2xl font-bold text-navy-900 outline-none focus:border-gold focus:ring-2 focus:ring-gold/30" />
      ))}
    </div>
  )
}

export interface OtpResult {
  token: string
  role: Role | null
  utilisateur: Utilisateur | null
}

/** Sends an OTP to `email` on mount, then verifies the code typed by the user. */
export default function OtpCode({ email, intention, onVerified }: {
  email: string
  intention: 'inscription' | 'connexion' | 'admin'
  onVerified: (r: OtpResult) => void
}) {
  const [otp, setOtp] = useState<OtpDemande | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [cooldown, setCooldown] = useState(0)
  const sent = useRef(false)

  const send = async () => {
    setBusy(true); setError('')
    try {
      const r = await authApi.demanderOtp(email, intention)
      setOtp(r); setCode(''); setCooldown(r.renvoi_dans_s)
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }

  useEffect(() => {
    if (sent.current) return   // StrictMode mounts twice in development: send only once
    sent.current = true
    void send()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown(cooldown - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const verify = async () => {
    setBusy(true); setError('')
    try {
      onVerified(await authApi.verifierOtp(email, code))
    } catch (e) { setError((e as Error).message); setCode('') } finally { setBusy(false) }
  }

  useEffect(() => {
    if (code.length === 6 && !busy) void verify()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

  return (
    <div className="mx-auto max-w-md py-2 text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-900 text-gold">
        {otp ? <MailCheck size={30} /> : <KeyRound size={30} />}
      </div>
      <h2 className="mt-4 text-2xl font-bold text-navy-900">Vérifiez votre e-mail</h2>
      <p className="mt-2 text-slate-600">
        {otp ? <>Nous avons envoyé un code à 6 chiffres à <b>{otp.destination_masquee}</b>.</> : busy ? 'Envoi du code…' : "Le code n'a pas pu être envoyé."}
      </p>
      <div className="mt-6"><OtpBoxes value={code} onChange={setCode} disabled={busy || !otp} /></div>
      {error && <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      <Button className="mt-6 w-full" onClick={verify} disabled={busy || code.length !== 6}>{busy && otp ? 'Vérification…' : 'Vérifier le code'}</Button>
      <div className="mt-4 text-sm text-slate-500">
        {cooldown > 0 ? <>Renvoyer un code dans <b>{cooldown} s</b></> : (
          <button onClick={send} disabled={busy} className="font-medium text-navy-900 underline decoration-gold underline-offset-4">Renvoyer un code</button>
        )}
      </div>
      <p className="mt-4 text-xs text-slate-400">Code valable 5 minutes · 5 tentatives maximum · usage unique. Pensez à vérifier vos courriers indésirables.</p>
    </div>
  )
}
