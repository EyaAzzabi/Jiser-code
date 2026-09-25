import { Handshake } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, dt, mdt, type ConciliationRow } from '../../api'
import { Badge, Card, ErrorBox, Kpi, Spinner } from '../../components/ui'
import { scoreTone } from './Stock'

export default function Conciliations() {
  const [rows, setRows] = useState<ConciliationRow[] | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => { api.conciliations().then(setRows).catch((e) => setError(e.message)) }, [])

  if (error) return <ErrorBox message={error} />
  if (!rows) return <Spinner label="Calcul des propositions…" />
  const propose = rows.reduce((s, r) => s + r.montant_propose, 0)
  const contentieux = rows.reduce((s, r) => s + r.montant_attendu_contentieux, 0)
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-navy-900">Conciliations proposées par l'IA</h1>
        <p className="mt-1 text-slate-500">Les dossiers où un accord amiable encaisse le plus, tout de suite, au lieu d'années de contentieux.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Kpi label="Dossiers à concilier" value={rows.length} />
        <Kpi label="Encaissable par conciliation" value={mdt(propose)} tone="success" hint="Montants proposés, payables maintenant" />
        <Kpi label="Espérance au contentieux" value={mdt(contentieux)} tone="warning" hint="En moyenne, après plusieurs années" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((r) => (
          <Card key={r.id} className="flex flex-col">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-semibold text-navy-900">{r.entreprise}</div>
                <div className="text-xs text-slate-500">{r.reference} · {r.gouvernorat}</div>
              </div>
              <Badge tone={scoreTone(r.score_solidite)}>{r.score_solidite}/100</Badge>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div><div className="text-xs text-slate-500">Notifié</div><div className="font-semibold">{dt(r.montant_total)}</div></div>
              <div><div className="text-xs text-slate-500">Proposé</div><div className="font-semibold text-emerald-700">{dt(r.montant_propose)}</div></div>
            </div>
            <div className="mt-3 h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-gold" style={{ width: `${Math.min(100, (r.montant_propose / r.montant_total) * 100)}%` }} />
            </div>
            <div className="mt-1 text-xs text-slate-500">{Math.round((r.montant_propose / r.montant_total) * 100)} % du montant notifié · {r.vices.length ? `${r.vices.length} vice(s) de procédure` : 'procédure régulière'}</div>
            <button onClick={() => navigate(`/administration/dossier/${r.id}`)} className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-navy-900 py-2 text-sm font-semibold text-white hover:bg-navy-800">
              <Handshake size={16} /> Examiner la proposition
            </button>
          </Card>
        ))}
      </div>
    </div>
  )
}
