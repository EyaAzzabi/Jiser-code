import clsx from 'clsx'
import { RefreshCw, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'

/** Visual signature of every AI intervention: gold border, "IA" badge, and which engine answered. */
export default function AiPanel({ title, mode, loading, onRefresh, children, className }: {
  title: string
  mode?: 'ia' | 'hors_ligne'
  loading?: boolean
  onRefresh?: () => void
  children: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('relative overflow-hidden rounded-2xl border border-gold/40 bg-gradient-to-br from-white to-gold-light/40 p-5 shadow-sm', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-gold to-gold-dark text-white shadow"><Sparkles size={16} /></span>
          <h3 className="font-semibold text-navy-900">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          {mode && (
            <span className={clsx('rounded-full px-2.5 py-0.5 text-[11px] font-semibold',
              mode === 'ia' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600')}>
              {mode === 'ia' ? 'Généré par l\'IA' : 'Version règles (IA indisponible)'}
            </span>
          )}
          {onRefresh && (
            <button onClick={onRefresh} disabled={loading} aria-label="Régénérer" className="rounded-lg p-1.5 text-slate-500 hover:bg-white hover:text-navy-900 disabled:opacity-40">
              <RefreshCw size={15} className={clsx(loading && 'animate-spin')} />
            </button>
          )}
        </div>
      </div>
      <div className="mt-3">
        {loading ? (
          <div className="space-y-2">
            {[90, 75, 82].map((w) => <div key={w} className="h-3 animate-pulse rounded bg-gold-light" style={{ width: `${w}%` }} />)}
          </div>
        ) : children}
      </div>
      <p className="mt-3 text-[11px] text-slate-400">Recommandation de l'IA, à valider par une personne habilitée.</p>
    </div>
  )
}
