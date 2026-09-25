import clsx from 'clsx'
import { AlertTriangle, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, dt, mdt, type Triage } from '../../api'
import { Badge, Card, ErrorBox, Kpi, Spinner } from '../../components/ui'

export const scoreTone = (s: number) => (s >= 60 ? 'emerald' : s >= 35 ? 'amber' : 'rose') as 'emerald' | 'amber' | 'rose'

export default function Stock() {
  const [data, setData] = useState<Triage | null>(null)
  const [groupe, setGroupe] = useState('')
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => {
    api.dossiers(groupe ? { groupe, limit: '100' } : { limit: '100' }).then(setData).catch((e) => setError(e.message))
  }, [groupe])

  const rows = useMemo(() => (data?.dossiers ?? []).filter((d) =>
    !q || `${d.entreprise} ${d.reference} ${d.gouvernorat}`.toLowerCase().includes(q.toLowerCase())), [data, q])

  if (error) return <ErrorBox message={error} />
  if (!data) return <Spinner label="Chargement des dossiers…" />
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-navy-900">Stock de dossiers</h1>
        <p className="mt-1 text-slate-500">Triés par l'IA : les dossiers en haut rapportent le plus. Priorité = montant recouvrable estimé × ancienneté.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Kpi label="Dossiers en cours" value={data.total} />
        <Kpi label="Montant bloqué" value={mdt(data.montant_total)} tone="danger" />
        <Kpi label="Montant recouvrable estimé" value={mdt(data.montant_recouvrable)} tone="success" hint="Somme des espérances du modèle" />
      </div>
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-1 text-sm font-medium text-slate-500">Groupes similaires :</span>
          <button onClick={() => setGroupe('')} className={clsx('rounded-lg px-3 py-1.5 text-sm', !groupe ? 'bg-navy-900 text-white' : 'bg-slate-100 hover:bg-slate-200')}>Tous</button>
          {data.groupes.map((g) => (
            <button key={g.groupe} onClick={() => setGroupe(g.groupe)}
              className={clsx('rounded-lg px-3 py-1.5 text-sm', groupe === g.groupe ? 'bg-navy-900 text-white' : 'bg-slate-100 hover:bg-slate-200')}>
              {g.groupe} <span className="opacity-60">· {g.nb}</span>
            </button>
          ))}
        </div>
      </Card>
      <Card className="overflow-x-auto p-0">
        <div className="flex items-center justify-between gap-3 p-4">
          <div className="relative w-full max-w-sm">
            <Search size={16} className="absolute left-3 top-3 text-slate-400" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher une entreprise, une référence…"
              className="w-full rounded-xl border border-slate-300 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-gold focus:ring-2 focus:ring-gold/30" />
          </div>
          <span className="text-sm text-slate-500">{rows.length} dossiers affichés</span>
        </div>
        <table className="w-full text-sm">
          <thead className="whitespace-nowrap bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">#</th><th className="px-4 py-2">Entreprise</th><th className="px-4 py-2">Étape</th>
              <th className="px-4 py-2 text-right">Notifié</th><th className="px-4 py-2 text-right">Recouvrable</th>
              <th className="px-4 py-2">Solidité</th><th className="px-4 py-2">Alertes</th><th className="px-4 py-2">Ancienneté</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((d, i) => (
              <tr key={d.id} onClick={() => navigate(`/administration/dossier/${d.id}`)} className="cursor-pointer hover:bg-gold-light/40">
                <td className="px-4 py-2.5 text-slate-400">{i + 1}</td>
                <td className="px-4 py-2.5"><div className="font-medium text-navy-900">{d.entreprise}</div><div className="text-xs text-slate-500">{d.reference} · {d.gouvernorat} · {d.groupe}</div></td>
                <td className="px-4 py-2.5 text-slate-600">{d.etape}</td>
                <td className="whitespace-nowrap px-4 py-2.5 text-right">{dt(d.montant_total)}</td>
                <td className="whitespace-nowrap px-4 py-2.5 text-right font-semibold text-emerald-700">{dt(d.montant_recouvrable)}</td>
                <td className="px-4 py-2.5"><Badge tone={scoreTone(d.score_solidite)}>{d.score_solidite}/100</Badge></td>
                <td className="px-4 py-2.5">{d.vices.length > 0 && <Badge tone="rose"><AlertTriangle size={12} className="mr-1" />{d.vices.length} vice(s)</Badge>}</td>
                <td className="whitespace-nowrap px-4 py-2.5 text-slate-500">{Math.round(d.anciennete_jours / 30)} mois</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
