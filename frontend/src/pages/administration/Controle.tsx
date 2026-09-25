import { Copy, FileUp } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, type Ameliorations, type Analyse } from '../../api'
import AiPanel from '../../components/AiPanel'
import AnalyseView from '../../components/AnalyseView'
import { Button, Card, ErrorBox, Spinner } from '../../components/ui'

export default function Controle() {
  const input = useRef<HTMLInputElement>(null)
  const [a, setA] = useState<Analyse | null>(null)
  const [amelio, setAmelio] = useState<Ameliorations | null>(null)
  const [amelioLoading, setAmelioLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async (f: File) => {
    setBusy(true); setError(''); setA(null); setAmelio(null)
    try {
      const r = await api.analyser(f, 'fr', '/api/admin/controle-qualite')
      setA(r)
      setAmelioLoading(true)
      api.ameliorer(r).then(setAmelio).catch(() => setAmelio(null)).finally(() => setAmelioLoading(false))
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-navy-900">Contrôle qualité avant envoi</h1>
        <p className="mt-1 text-slate-500">Déposez votre projet de notification : JISER signale les vices de procédure et l'IA réécrit les motivations trop faibles, pour éviter une annulation au tribunal.</p>
      </div>
      <Card>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => input.current?.click()} disabled={busy}><FileUp size={16} /> Déposer un projet de notification</Button>
          <Button variant="light" onClick={async () => run(await api.exempleBlob('notification_sami.pdf'))} disabled={busy}>Tester avec le projet « Sfax »</Button>
          <input ref={input} type="file" accept=".pdf,.txt,.png,.jpg,.jpeg" className="hidden" onChange={(e) => e.target.files?.[0] && run(e.target.files[0])} />
        </div>
      </Card>
      {busy && <Spinner label="Contrôle en cours…" />}
      {error && <ErrorBox message={error} />}
      {a && (
        <>
          <AiPanel title="Motivations réécrites par l'IA" mode={amelio?.mode} loading={amelioLoading}>
            {amelio && (amelio.ameliorations.length === 0 ? (
              <p className="text-sm text-emerald-700">Tous les chefs sont correctement motivés et fondés.</p>
            ) : (
              <div className="space-y-3">
                {amelio.ameliorations.map((m) => (
                  <div key={m.chef_id} className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
                    <div className="text-sm font-semibold text-navy-900">Chef {m.chef_id} · <span className="text-rose-600">{m.probleme}</span></div>
                    <p className="mt-2 rounded-lg bg-canvas p-3 text-sm text-slate-700">{m.motivation_proposee}</p>
                    <button onClick={() => navigator.clipboard.writeText(m.motivation_proposee)} className="mt-2 flex items-center gap-1 text-xs font-medium text-navy-800 hover:text-gold-dark"><Copy size={12} /> Copier la motivation</button>
                  </div>
                ))}
              </div>
            ))}
          </AiPanel>
          <AnalyseView a={a} mode="controle" />
        </>
      )}
    </div>
  )
}
