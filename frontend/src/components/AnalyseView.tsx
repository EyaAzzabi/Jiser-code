import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Clock, HelpCircle, Languages, Sparkles } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { articleLabel, dt, frDate, type Analyse, type ChefAnalyse, type ProcedureCheck } from '../api'
import { StarButton } from './Favoris'
import ListenButton from './ListenButton'
import { Card, ContestBadge, Kpi, SectionTitle } from './ui'

export function ProcedureList({ checks }: { checks: ProcedureCheck[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {checks.map((c) => (
        <li key={c.code} className="flex gap-3 py-2.5 text-sm">
          {c.statut === 'ok' ? <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-500" size={18} />
            : c.statut === 'vice' ? <AlertTriangle className="mt-0.5 shrink-0 text-rose-500" size={18} />
              : <HelpCircle className="mt-0.5 shrink-0 text-amber-500" size={18} />}
          <div>
            <div className="font-medium text-slate-800">{c.label} <span className="text-xs font-normal text-slate-400">· {articleLabel(c.article)}</span></div>
            <div className={c.statut === 'vice' ? 'text-rose-700' : 'text-slate-500'}>{c.detail}</div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ChefCard({ ca, aiMode, langue }: { ca: ChefAnalyse; aiMode: boolean; langue: 'fr' | 'derja' }) {
  const [open, setOpen] = useState<string | null>(null)
  const c = ca.chef
  const article = ca.articles.find((x) => x.id === open)
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-400">CHEF {c.id.replace('C', 'N°')} · {c.impot} · exercice {c.exercice}</div>
          <h3 className="mt-1 font-semibold text-navy-900">{c.libelle}</h3>
        </div>
        <div className="text-right">
          <div className="font-display text-xl font-bold text-navy-900">{dt(c.montant_principal + c.penalites)}</div>
          <div className="text-xs text-slate-500">dont {dt(c.penalites)} de pénalités</div>
        </div>
      </div>
      <div className="mt-3"><ContestBadge value={ca.contestabilite} /></div>
      <div className="mt-3 rounded-xl bg-bridge-light p-3 text-sm text-slate-700">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-1 font-semibold text-navy-900">{aiMode && <Sparkles size={14} className="text-gold" />}En clair :</span>
          <ListenButton text={ca.explication} source={langue} />
        </div>
        <p className="mt-1">{ca.explication}</p>
      </div>
      {c.motivation && <p className="mt-2 text-xs italic text-slate-500">Motivation de l'administration : « {c.motivation} »</p>}
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <div className="text-sm font-semibold text-slate-700">Arguments de réponse</div>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-600">{ca.arguments.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-700">Pièces à rassembler</div>
          <ul className="mt-1 space-y-1 text-sm text-slate-600">{ca.pieces_a_fournir.map((p) => <li key={p}>☐ {p}</li>)}</ul>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {ca.articles.map((a) => (
          <button key={a.id} onClick={() => setOpen(open === a.id ? null : a.id)}
            className={clsx('rounded-lg px-2.5 py-1 text-xs font-medium ring-1', open === a.id ? 'bg-navy-900 text-white ring-navy-900' : 'bg-white text-navy-800 ring-slate-300 hover:ring-gold')}>
            {articleLabel(a.id)}
          </button>
        ))}
      </div>
      {article && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
          {article.extrait}
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <a href={article.source_url} target="_blank" rel="noreferrer" className="text-navy-800 underline decoration-gold">Source : Jurisite Tunisie</a>
            <StarButton type="article" refId={article.id} titre={articleLabel(article.id)} extrait={article.extrait} label />
          </div>
        </div>
      )}
    </Card>
  )
}

export default function AnalyseView({ a, mode = 'entreprise', onLangue, langueBusy, actions }: {
  a: Analyse
  mode?: 'entreprise' | 'controle'
  onLangue?: (l: 'fr' | 'derja') => void
  langueBusy?: boolean
  actions?: ReactNode
}) {
  const n = a.notification
  const vices = a.procedure.filter((p) => p.statut === 'vice').length
  return (
    <div className="space-y-6">
      <Card tone="dark">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-gold">{n.centre}</div>
            <div className="text-xl font-semibold">{n.entreprise.nom}</div>
            <div className="text-sm text-slate-300">Notification {n.reference} du {frDate(n.date_notification)} · vérification {n.type_verification} · exercices {n.exercices_verifies.join(', ')}</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {actions}
            {onLangue && (
              <div className="flex rounded-xl bg-white/10 p-1 text-sm">
                <Languages size={16} className="mx-1.5 self-center text-gold" />
                {(['fr', 'derja'] as const).map((l) => (
                  <button key={l} disabled={langueBusy} onClick={() => onLangue(l)}
                    className={clsx('rounded-lg px-3 py-1 font-medium', a.langue === l ? 'bg-white text-navy-900' : 'text-slate-200 hover:bg-white/10')}>
                    {l === 'fr' ? 'Français' : 'Tounsi'}
                  </button>
                ))}
              </div>
            )}
            <span className={clsx('flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold', a.mode === 'ia' ? 'bg-gold text-white' : 'bg-white/15 text-slate-200')}>
              {a.mode === 'ia' ? <><Sparkles size={12} /> Analyse IA</> : 'Règles + modèle ML'}
            </span>
          </div>
        </div>
        <div className={clsx('mt-4 rounded-xl bg-white/10 p-3 text-sm', langueBusy && 'animate-pulse')}>
          <p>{a.resume}</p>
          <div className="mt-3"><ListenButton text={a.resume} source={a.langue} tone="dark" /></div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Kpi label="Montant réclamé" value={dt(a.montant_total)} />
        <Kpi label="Montant contestable estimé" value={dt(a.montant_contestable)} tone="warning" hint="Selon le modèle et les règles du CDPF" />
        {mode === 'entreprise'
          ? <Kpi label="Date limite de réponse" value={frDate(a.date_limite_reponse)} tone={a.jours_restants <= 7 ? 'danger' : 'default'}
            hint={<span className="flex items-center gap-1"><Clock size={12} /> {a.jours_restants >= 0 ? `Il reste ${a.jours_restants} jours` : 'Délai dépassé'}</span>} />
          : <Kpi label="Chefs fragiles" value={`${a.chefs.filter((c) => c.contestabilite !== 'solide').length} / ${a.chefs.length}`} tone="warning" />}
        <Kpi label="Vices de procédure" value={vices} tone={vices ? 'danger' : 'success'} hint={vices ? 'Voir le contrôle ci-dessous' : 'Procédure régulière'} />
      </div>

      <Card>
        <SectionTitle sub="Chaque point est vérifié par rapport au Code des droits et procédures fiscaux.">Contrôle de la procédure</SectionTitle>
        <ProcedureList checks={a.procedure} />
      </Card>

      <div>
        <SectionTitle sub={mode === 'entreprise' ? "Ce qu'on vous reproche, et ce que vous pouvez répondre." : 'Points faibles à renforcer avant envoi.'}>Chefs de redressement</SectionTitle>
        <div className={clsx('space-y-4', langueBusy && 'opacity-60')}>{a.chefs.map((ca) => <ChefCard key={ca.chef.id} ca={ca} aiMode={a.mode === 'ia'} langue={a.langue} />)}</div>
      </div>
    </div>
  )
}
