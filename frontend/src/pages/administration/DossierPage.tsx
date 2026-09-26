import clsx from 'clsx'
import { ArrowLeft, Copy, MessagesSquare, ThumbsDown, ThumbsUp, UserCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, dt, frDate, messagerieApi, type AvisDossier, type DossierDetail } from '../../api'
import AiPanel from '../../components/AiPanel'
import ExportMenu from '../../components/ExportMenu'
import { StarButton } from '../../components/Favoris'
import ListenButton from '../../components/ListenButton'
import { Badge, Button, Card, ErrorBox, Kpi, ScoreGauge, SectionTitle, Spinner } from '../../components/ui'

export default function DossierPage() {
  const { id } = useParams()
  const [d, setD] = useState<DossierDetail | null>(null)
  const [avis, setAvis] = useState<AvisDossier | null>(null)
  const [avisLoading, setAvisLoading] = useState(true)
  const [error, setError] = useState('')
  const [decision, setDecision] = useState<{ statut: string; message: string } | null>(null)
  const [conv, setConv] = useState<string | null>(null)
  const decide = async (v: 'validee' | 'refusee') => {
    if (!id) return
    try { setDecision(await api.decision(id, v)) } catch (e) { setError((e as Error).message) }
  }
  const navigate = useNavigate()

  const loadAvis = () => {
    if (!id) return
    setAvisLoading(true)
    api.avisIA(id).then(setAvis).catch(() => setAvis(null)).finally(() => setAvisLoading(false))
  }
  useEffect(() => {
    if (!id) return
    api.dossier(id).then(setD).catch((e) => setError(e.message))
    messagerieApi.duDossier(id).then((r) => setConv(r.conversation?.id ?? null)).catch(() => {})
    loadAvis()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (error) return <ErrorBox message={error} />
  if (!d) return <Spinner label="Calcul du score…" />
  const n = d.dossier.notification
  const total = d.conciliation.montant_notifie
  const maxImpact = Math.max(...d.score.explications.map((e) => Math.abs(e.impact)), 0.01)
  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/administration/dossiers')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-navy-900"><ArrowLeft size={14} /> Retour au stock</button>
      <Card tone="dark">
        <div className="text-xs uppercase tracking-wide text-gold">{n.centre} · {d.dossier.etape}</div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-2xl font-semibold">{n.entreprise.nom}</div>
          <div className="flex flex-wrap gap-2">
            <StarButton type="dossier_admin" refId={d.dossier.id} tone="dark" titre={`Dossier ${n.reference} · ${n.entreprise.nom}`}
              extrait={`Score ${d.score.score_solidite}/100 · ${dt(total)} notifiés · conciliation proposée ${dt(d.conciliation.montant_propose)}`} lien={`/administration/dossier/${d.dossier.id}`} />
            <ExportMenu tone="dark" url={`/api/admin/dossiers/${d.dossier.id}/pdf`} filename={`JISER_dossier_${n.reference}.pdf`}
              subject={`Dossier ${n.reference} · ${n.entreprise.nom}`}
              body={`Bonjour,\n\nCi-joint la fiche JISER du dossier ${n.reference} (score de solidité ${d.score.score_solidite}/100), avec l'avis juridique et la proposition de conciliation.`} />
          </div>
        </div>
        <div className="text-sm text-slate-300">{n.reference} · notifiée le {frDate(n.date_notification)} · {n.entreprise.secteur} · {n.entreprise.gouvernorat} · {n.chefs.length} chef(s) · {dt(total)}</div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <span className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1"><UserCheck size={14} className="text-gold" />
            {d.affectation ? `Affecté à ${d.affectation.agent_nom}` : 'Non affecté'}</span>
          {conv
            ? <button onClick={() => navigate(`/administration/messagerie/${conv}`)} className="flex items-center gap-1.5 rounded-full bg-gold px-3 py-1 font-semibold text-white hover:bg-gold-dark"><MessagesSquare size={14} /> Conversation avec l'entreprise</button>
            : <span className="text-xs text-slate-300">L'entreprise n'a pas encore ouvert d'échange sur JISER.</span>}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="flex flex-col items-center">
          <SectionTitle>Score de solidité</SectionTitle>
          <ScoreGauge score={d.score.score_solidite} />
          <p className="mt-2 text-center text-sm text-slate-600">Probabilité que le redressement tienne devant le juge : <b>{Math.round(d.score.proba_maintien * 100)} %</b></p>
          <p className="text-center text-sm text-slate-600">Montant recouvrable estimé : <b className="text-emerald-700">{dt(d.score.montant_recouvrable_estime)}</b></p>
        </Card>
        <Card className="lg:col-span-2">
          <SectionTitle sub="Contribution de chaque facteur au score (méthode SHAP). Rouge : affaiblit le dossier ; vert : le renforce.">Pourquoi ce score ?</SectionTitle>
          <ul className="space-y-2.5">
            {d.score.explications.map((e) => (
              <li key={e.facteur} className="text-sm">
                <div className="flex justify-between"><span>{e.facteur}</span><span className={e.impact < 0 ? 'text-rose-600' : 'text-emerald-600'}>{e.impact > 0 ? '+' : ''}{e.impact.toFixed(2)}</span></div>
                <div className="mt-1 h-2 rounded-full bg-slate-100"><div className={clsx('h-2 rounded-full', e.impact < 0 ? 'bg-rose-400' : 'bg-emerald-400')} style={{ width: `${(Math.abs(e.impact) / maxImpact) * 100}%` }} /></div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <AiPanel title="Avis juridique de l'IA" mode={avis?.mode} loading={avisLoading} onRefresh={loadAvis}>
        {avis && (
          <div className="space-y-4">
            <p className="text-sm leading-relaxed text-slate-700">{avis.avis}</p>
            <ListenButton text={avis.avis} />
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl bg-emerald-50 p-3"><div className="text-sm font-semibold text-emerald-800">Points forts</div>
                <ul className="mt-1 list-disc pl-5 text-sm text-emerald-900">{avis.points_forts.map((p) => <li key={p}>{p}</li>)}</ul></div>
              <div className="rounded-xl bg-rose-50 p-3"><div className="text-sm font-semibold text-rose-800">Points faibles</div>
                <ul className="mt-1 list-disc pl-5 text-sm text-rose-900">{avis.points_faibles.map((p) => <li key={p}>{p}</li>)}</ul></div>
            </div>
          </div>
        )}
      </AiPanel>

      <Card className="overflow-x-auto">
        <SectionTitle sub={d.conciliation.commentaire}>Proposition de conciliation</SectionTitle>
        <table className="w-full text-sm">
          <thead className="whitespace-nowrap text-left text-xs uppercase text-slate-500">
            <tr><th className="py-2">Chef</th><th className="py-2 pl-4 text-right">Notifié</th><th className="py-2 pl-4 text-right">Chance de maintien</th><th className="py-2 pl-4">Recommandation</th><th className="py-2 text-right">Proposé</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {d.conciliation.items.map((it) => (
              <tr key={it.chef_id}>
                <td className="py-2.5 pr-4"><div className="font-medium">{it.chef_id} · {it.libelle}</div><div className="text-xs text-slate-500">{it.justification}</div></td>
                <td className="whitespace-nowrap py-2.5 text-right">{dt(it.montant)}</td>
                <td className="py-2.5 text-right">{Math.round(it.p_maintenu * 100)} %</td>
                <td className="py-2.5 pl-4"><Badge tone={it.action === 'maintenir' ? 'emerald' : it.action === 'transiger' ? 'amber' : 'rose'}>{it.action}</Badge></td>
                <td className="whitespace-nowrap py-2.5 text-right font-semibold">{dt(it.montant_propose)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Kpi label="Montant notifié" value={dt(total)} />
          <Kpi label="Accord proposé (encaissé maintenant)" value={dt(d.conciliation.montant_propose)} tone="success" />
          <Kpi label="Espérance au contentieux (dans des années)" value={dt(d.conciliation.montant_attendu_contentieux)} tone="warning" />
        </div>
      </Card>

      {avis && (
        <AiPanel title="Projet de lettre de conciliation" mode={avis.mode}>
          <textarea defaultValue={avis.lettre_conciliation} rows={12} className="w-full rounded-xl border border-slate-300 bg-white p-4 font-mono text-xs leading-relaxed" />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button variant="light" onClick={() => navigator.clipboard.writeText(avis.lettre_conciliation)}><Copy size={14} /> Copier</Button>
            <span className="mx-2 h-6 w-px bg-slate-200" />
            <span className="text-sm text-slate-600">Décision de l'agent :</span>
            <Button variant={decision?.statut && decision.statut !== 'refusee' ? 'primary' : 'ghost'} onClick={() => decide('validee')}><ThumbsUp size={14} /> Valider</Button>
            <Button variant={decision?.statut === 'refusee' ? 'primary' : 'ghost'} onClick={() => decide('refusee')}><ThumbsDown size={14} /> Refuser</Button>
            {decision && <span className={clsx('text-sm font-medium', decision.statut === 'en_attente_validation' ? 'text-gold-dark' : 'text-emerald-700')}>{decision.message} Inscrit au journal.</span>}
          </div>
        </AiPanel>
      )}
    </div>
  )
}
