import { Handshake, ThumbsDown, ThumbsUp, UserPlus, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, dt, pilotageApi, type Agent, type ConciliationAValider, type DossierRow } from '../../api'
import DemandesAcces from '../../components/DemandesAcces'
import { Badge, Button, Card, ErrorBox, PageHeader, SectionTitle, Spinner } from '../../components/ui'

/** Head of centre: team workload, file assignment, settlement approvals, officer accounts. */
export default function Equipe() {
  const [agents, setAgents] = useState<Agent[] | null>(null)
  const [dossiers, setDossiers] = useState<DossierRow[]>([])
  const [valider, setValider] = useState<ConciliationAValider[] | null>(null)
  const [choix, setChoix] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const charger = () => {
    pilotageApi.equipe().then(setAgents).catch((e) => setError(e.message))
    pilotageApi.aValider().then(setValider).catch((e) => setError(e.message))
    api.dossiers({ limit: '40' }).then((t) => setDossiers(t.dossiers)).catch(() => {})
  }
  useEffect(charger, [])

  const affecter = async (d: DossierRow) => {
    const agent = choix[d.id]
    if (!agent) return
    try { await pilotageApi.affecter(d.id, agent); setMsg(`Dossier ${d.reference} affecté.`); charger() } catch (e) { setError((e as Error).message) }
  }
  const decider = async (c: ConciliationAValider, decision: 'validee' | 'refusee') => {
    try { await pilotageApi.deciderConciliation(c.id, decision); setMsg(`Conciliation ${c.reference} ${decision === 'validee' ? 'validée' : 'refusée'} (inscrite au journal).`); charger() }
    catch (e) { setError((e as Error).message) }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Chef de centre" title="Équipe et validations"
        subtitle="Affectez les dossiers, validez les conciliations au-dessus du seuil et les comptes des agents de votre centre." />
      {error && <ErrorBox message={error} />}
      {msg && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{msg}</div>}

      <Card>
        <SectionTitle sub="Proposées par vos agents : au-delà du seuil, votre validation est obligatoire."><span className="flex items-center gap-2"><Handshake size={18} className="text-gold-dark" /> Conciliations à valider</span></SectionTitle>
        {!valider ? <Spinner /> : valider.length === 0 ? <p className="text-sm text-slate-500">Aucune proposition en attente.</p> : (
          <ul className="divide-y divide-slate-100">
            {valider.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-3 py-3">
                <div className="flex-1"><Link to={`/administration/dossier/${c.dossier_id}`} className="font-semibold text-navy-900 hover:underline">{c.reference}</Link>
                  <div className="text-xs text-slate-500">Proposé par {c.propose_par} · notifié {dt(c.montant_notifie)}</div></div>
                <div className="font-display text-lg font-bold text-emerald-700">{dt(c.montant_propose)}</div>
                <Button variant="gold" onClick={() => decider(c, 'validee')}><ThumbsUp size={14} /> Valider</Button>
                <Button variant="ghost" onClick={() => decider(c, 'refusee')}><ThumbsDown size={14} /> Refuser</Button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-2">
          <SectionTitle sub="Agents actifs de votre centre et leur charge"><span className="flex items-center gap-2"><Users size={18} className="text-gold-dark" /> Mon équipe</span></SectionTitle>
          {!agents ? <Spinner /> : agents.length === 0 ? <p className="text-sm text-slate-500">Aucun agent validé dans votre centre pour le moment.</p> : (
            <ul className="space-y-3">
              {agents.map((a) => {
                const max = Math.max(...agents.map((x) => x.dossiers), 1)
                return (
                  <li key={a.id}>
                    <div className="flex justify-between text-sm"><span className="font-medium text-navy-900">{a.nom}</span><span className="text-slate-500">{a.dossiers} dossier(s) · {dt(a.montant)}</span></div>
                    <div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-navy-900" style={{ width: `${(a.dossiers / max) * 100}%` }} /></div>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
        <Card className="overflow-x-auto p-0 xl:col-span-3">
          <div className="p-5 pb-0"><SectionTitle sub="Les plus prioritaires de votre centre (montant recouvrable × ancienneté).">Affecter les dossiers</SectionTitle></div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-4 py-2">Dossier</th><th className="px-4 py-2 text-right">Recouvrable</th><th className="px-4 py-2">Agent</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {dossiers.slice(0, 15).map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-2"><Link to={`/administration/dossier/${d.id}`} className="font-medium text-navy-900 hover:underline">{d.entreprise}</Link><div className="text-xs text-slate-500">{d.reference}</div></td>
                  <td className="px-4 py-2 text-right font-medium">{dt(d.montant_recouvrable)}</td>
                  <td className="px-4 py-2">
                    {d.affecte_a ? <Badge tone="emerald">{d.affecte_a}</Badge> : (
                      <div className="flex gap-2">
                        <select value={choix[d.id] ?? ''} onChange={(e) => setChoix({ ...choix, [d.id]: e.target.value })} className="rounded-lg border border-slate-300 px-2 py-1 text-xs">
                          <option value="">Choisir…</option>{agents?.map((a) => <option key={a.id} value={a.id}>{a.nom}</option>)}
                        </select>
                        <button onClick={() => affecter(d)} disabled={!choix[d.id]} className="rounded-lg bg-navy-900 p-1.5 text-white disabled:opacity-30" aria-label="Affecter"><UserPlus size={14} /></button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-navy-900">Comptes d'agents à valider</h2>
        <DemandesAcces vide="Aucun agent de votre centre en attente de validation." />
      </div>
    </div>
  )
}
