import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Clock, FileText, UserCheck, UserX, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { comptesApi, type Demande } from '../api'
import { Badge, Button, Card, ErrorBox, Spinner } from './ui'

/** Validation queue for new accounts (platform admin: everyone; head of centre: the officers of the centre). */
export default function DemandesAcces({ vide = 'Aucune demande en attente.' }: { vide?: string }) {
  const [rows, setRows] = useState<Demande[] | null>(null)
  const [motifs, setMotifs] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const charger = () => comptesApi.demandes().then(setRows).catch((e) => setError(e.message))
  useEffect(() => { void charger() }, [])

  const decider = async (d: Demande, decision: 'valide' | 'refuse') => {
    setError(''); setMsg('')
    try {
      await comptesApi.decider(d.id, decision, motifs[d.id] ?? '')
      setMsg(`${d.prenom} ${d.nom} : ${decision === 'valide' ? 'compte activé, e-mail de confirmation envoyé' : 'demande refusée, motif communiqué'}.`)
      void charger()
    } catch (e) { setError((e as Error).message) }
  }
  const voir = async (id: string) => { try { window.open(await comptesApi.pieceUrl(id), '_blank') } catch (e) { setError((e as Error).message) } }

  if (!rows) return <Spinner />
  return (
    <div className="space-y-4">
      {error && <ErrorBox message={error} />}
      {msg && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{msg}</div>}
      {rows.length === 0 && <Card><p className="text-sm text-slate-500">{vide}</p></Card>}
      {rows.map((d) => {
        const pv = d.verification.pre_verification
        const retard = d.attente_heures >= 20
        return (
          <Card key={d.id}>
            <div className="flex flex-wrap items-start gap-4">
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-lg font-semibold text-navy-900">{d.prenom} {d.nom}</span>
                  <Badge tone={d.role === 'entreprise' ? 'sky' : 'gold'}>{d.role_label}</Badge>
                  <span className={clsx('flex items-center gap-1 text-xs', retard ? 'font-semibold text-rose-600' : 'text-slate-500')}>
                    <Clock size={12} /> en attente depuis {d.attente_heures < 1 ? `${Math.round(d.attente_heures * 60)} min` : `${Math.round(d.attente_heures)} h`}{retard && ' · délai de 24 h bientôt dépassé'}</span>
                </div>
                <div className="text-sm text-slate-500">{d.email} · {String(d.details.raison_sociale ?? (d.details.centre ? `CRCI ${d.details.centre}` : d.details.cabinet ?? ''))}
                  {d.details.matricule_fiscal ? ` · ${String(d.details.matricule_fiscal)}` : ''}{d.details.matricule_agent ? ` · matricule ${String(d.details.matricule_agent)}` : ''}</div>
              </div>
              {pv && (
                <div className={clsx('rounded-2xl px-4 py-2 text-center', pv.score >= 80 ? 'bg-emerald-50 text-emerald-700' : pv.score >= 50 ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700')}>
                  <div className="font-display text-2xl font-bold">{pv.score} %</div><div className="text-[11px]">pré-vérification</div>
                </div>
              )}
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <ul className="space-y-1 text-sm">
                {pv?.controles.map((c) => (
                  <li key={c.controle} className="flex items-start gap-2">
                    {c.statut === 'ok' ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-600" /> : c.statut === 'alerte' ? <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-500" /> : <XCircle size={16} className="mt-0.5 shrink-0 text-rose-600" />}
                    <span><span className="text-slate-700">{c.controle}</span> <span className="text-xs text-slate-500">· {c.detail}</span></span>
                  </li>
                ))}
              </ul>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Justificatifs (chiffrés)</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {d.pieces.length === 0 && <span className="text-sm text-rose-600">Aucune pièce déposée</span>}
                  {d.pieces.map((p) => (
                    <button key={p.id} onClick={() => voir(p.id)} className="flex items-center gap-1.5 rounded-lg bg-canvas px-3 py-1.5 text-sm text-navy-900 ring-1 ring-slate-200 hover:ring-gold">
                      <FileText size={14} className="text-gold-dark" />{p.nom}
                    </button>
                  ))}
                </div>
                <input value={motifs[d.id] ?? ''} onChange={(e) => setMotifs({ ...motifs, [d.id]: e.target.value })} placeholder="Motif (obligatoire en cas de refus, communiqué au demandeur)"
                  className="mt-4 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" />
                <div className="mt-2 flex gap-2">
                  <Button variant="gold" onClick={() => decider(d, 'valide')}><UserCheck size={16} /> Valider l'accès</Button>
                  <Button variant="ghost" onClick={() => decider(d, 'refuse')} disabled={!(motifs[d.id] ?? '').trim()}><UserX size={16} /> Refuser</Button>
                </div>
              </div>
            </div>
          </Card>
        )
      })}
    </div>
  )
}
