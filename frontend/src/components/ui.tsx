import clsx from 'clsx'
import type { ReactNode } from 'react'
import type { Contestabilite } from '../api'

export function Card({ children, className, tone = 'light' }: { children: ReactNode; className?: string; tone?: 'light' | 'dark' }) {
  return (
    <div className={clsx('rounded-2xl p-5',
      tone === 'dark'
        ? 'bg-gradient-to-br from-navy-900 to-navy-700 text-white shadow-lg shadow-navy-900/20'
        : 'border border-slate-200/80 bg-white shadow-sm',
      className)}>
      {children}
    </div>
  )
}

/** Page header shared by every space, with the gold accent bar from the logo. */
export function PageHeader({ eyebrow, title, subtitle, actions }: { eyebrow?: string; title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <div className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">{eyebrow}</div>}
        <h1 className="mt-1 text-3xl font-bold text-navy-900">{title}</h1>
        <div className="mt-2 h-1 w-14 rounded-full bg-gold" />
        {subtitle && <p className="mt-3 max-w-2xl text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  )
}

export function Kpi({ label, value, hint, tone = 'default' }: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'default' | 'danger' | 'success' | 'warning'
}) {
  const color = {
    default: 'text-navy-900',
    danger: 'text-rose-600',
    success: 'text-emerald-600',
    warning: 'text-gold-dark',
  }[tone]
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={clsx('mt-1 font-display text-2xl font-bold', color)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </Card>
  )
}

const CONTEST_STYLE: Record<Contestabilite, string> = {
  solide: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  discutable: 'bg-amber-50 text-amber-700 ring-amber-200',
  contestable: 'bg-rose-50 text-rose-700 ring-rose-200',
}
const CONTEST_LABEL: Record<Contestabilite, string> = {
  solide: '🟢 Solide',
  discutable: '🟠 Discutable',
  contestable: '🔴 Contestable',
}

export function ContestBadge({ value }: { value: Contestabilite }) {
  return (
    <span className={clsx('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1', CONTEST_STYLE[value])}>
      {CONTEST_LABEL[value]}
    </span>
  )
}

export function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: 'slate' | 'rose' | 'emerald' | 'amber' | 'sky' | 'gold' }) {
  const styles = {
    slate: 'bg-slate-100 text-slate-700',
    rose: 'bg-rose-100 text-rose-700',
    emerald: 'bg-emerald-100 text-emerald-700',
    amber: 'bg-amber-100 text-amber-800',
    sky: 'bg-bridge-light text-navy-800',
    gold: 'bg-gold-light text-gold-dark',
  }[tone]
  return <span className={clsx('inline-flex items-center whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium', styles)}>{children}</span>
}

export function Button({ children, onClick, variant = 'primary', disabled, className, type = 'button' }: {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'gold' | 'ghost' | 'light'
  disabled?: boolean
  className?: string
  type?: 'button' | 'submit'
}) {
  const styles = {
    primary: 'bg-navy-900 text-white hover:bg-navy-800',
    gold: 'bg-gold text-white hover:bg-gold-dark',
    ghost: 'bg-white text-navy-900 ring-1 ring-slate-300 hover:bg-slate-50',
    light: 'bg-slate-100 text-navy-900 hover:bg-slate-200',
  }[variant]
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={clsx('inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50', styles, className)}>
      {children}
    </button>
  )
}

export function ScoreGauge({ score }: { score: number }) {
  const color = score >= 60 ? '#059669' : score >= 35 ? '#c29a2e' : '#e11d48'
  const angle = (score / 100) * 180
  const rad = (Math.PI * (180 - angle)) / 180
  const x = 60 + 48 * Math.cos(rad)
  const y = 60 - 48 * Math.sin(rad)
  return (
    <svg viewBox="0 0 120 70" className="w-44" role="img" aria-label={`Score ${score} sur 100`}>
      <path d="M12 60 A48 48 0 0 1 108 60" fill="none" stroke="#e2e8f0" strokeWidth="10" strokeLinecap="round" />
      {score > 0 && <path d={`M12 60 A48 48 0 0 1 ${x} ${y}`} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" />}
      <text x="60" y="56" textAnchor="middle" fontSize="22" fontWeight="700" fill={color}>{score}</text>
      <text x="60" y="68" textAnchor="middle" fontSize="7" fill="#64748b">/ 100</text>
    </svg>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-slate-500">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-gold" />
      {label}
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{message}</div>
}

export function SectionTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-navy-900">{children}</h2>
      {sub && <p className="text-sm text-slate-500">{sub}</p>}
    </div>
  )
}

/** Dismissible contextual help shown once per space (part of the onboarding). */
export function TipBanner({ id, title, steps }: { id: string; title: string; steps: string[] }) {
  const key = `jiser-tip-${id}`
  let hidden = false
  try { hidden = localStorage.getItem(key) === '1' } catch { /* storage unavailable */ }
  if (hidden) return null
  return (
    <div className="relative rounded-2xl border border-gold/30 bg-gold-light/60 p-4">
      <button aria-label="Masquer l'aide" className="absolute right-3 top-2 text-lg leading-none text-gold-dark hover:text-navy-900"
        onClick={(e) => {
          try { localStorage.setItem(key, '1') } catch { /* ignore */ }
          ;(e.currentTarget.parentElement as HTMLElement).style.display = 'none'
        }}>×</button>
      <div className="font-semibold text-navy-900">💡 {title}</div>
      <ol className="mt-2 grid gap-2 text-sm text-slate-700 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={s} className="flex gap-2">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs font-bold text-white">{i + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
