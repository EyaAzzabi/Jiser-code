import clsx from 'clsx'
import { AlertTriangle, ArrowLeft, FileUp } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { NavLink, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { api, dt, frDate, mdt, type Analyse, type Dashboard, type DossierDetail, type Triage } from '../api'
import { Badge, Card, ErrorBox, Kpi, PageHeader, ScoreGauge, SectionTitle, Spinner, TipBanner } from '../components/ui'
import { AnalyseView } from './Entreprise'

const TABS = [
  { to: '/administration', label: 'Stock de dossiers', end: true },
  { to: '/administration/tableau-de-bord', label: 'Tableau de bord' },
  { to: '/administration/controle-qualite', label: 'Contrôle qualité avant envoi' },
]

function scoreTone(s: number) {
  return s >= 60 ? 'emerald' : s >= 35 ? 'amber' : 'rose'
}

function Stock() {
  const [data, setData] = useState<Triage | null>(null)
  const [groupe, setGroupe] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => {
    api.dossiers(groupe ? { groupe, limit: '60' } : { limit: '60' }).then(setData).catch((e) => setError(e.message))
  }, [groupe])

  if (error) return <ErrorBox message={error} />
  if (!data) return <Spinner label="Chargement des dossiers…" />
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Kpi label="Dossiers en cours" value={data.total} />
        <Kpi label="Montant bloqué" value={mdt(data.montant_total)} tone="danger" />
        <Kpi label="Montant recouvrable estimé" value={mdt(data.montant_recouvrable)} tone="success" hint="Somme des espérances du modèle" />
      </div>
      <Card>
        <SectionTitle sub="Regrouper les dossiers similaires permet de les confier au même agent.">Groupes de dossiers similaires</SectionTitle>
        <div className="flex flex-wrap gap-2">
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
        <div className="p-5 pb-0"><SectionTitle sub="Priorité = montant recouvrable estimé × ancienneté. Cliquez sur un dossier pour le détail.">Dossiers triés par priorité</SectionTitle></div>
        <table className="w-full text-sm">
          <thead className="whitespace-nowrap bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">#</th><th className="px-4 py-2">Entreprise</th><th className="px-4 py-2">Étape</th>
              <th className="px-4 py-2 text-right">Notifié</th><th className="px-4 py-2 text-right">Recouvrable</th>
              <th className="px-4 py-2">Solidité</th><th className="px-4 py-2">Alertes</th><th className="px-4 py-2">Ancienneté</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.dossiers.map((d, i) => (
              <tr key={d.id} onClick={() => navigate(`/administration/dossier/${d.id}`)} className="cursor-pointer hover:bg-gold-light/40">
                <td className="px-4 py-2.5 text-slate-400">{i + 1}</td>
                <td className="px-4 py-2.5"><div className="font-medium text-navy-900">{d.entreprise}</div><div className="text-xs text-slate-500">{d.reference} · {d.gouvernorat} · {d.groupe}</div></td>
                <td className="px-4 py-2.5 text-slate-600">{d.etape}</td>
                <td className="px-4 py-2.5 text-right">{dt(d.montant_total)}</td>
                <td className="px-4 py-2.5 text-right font-semibold text-emerald-700">{dt(d.montant_recouvrable)}</td>
                <td className="px-4 py-2.5"><Badge tone={scoreTone(d.score_solidite)}>{d.score_solidite}/100</Badge></td>
                <td className="px-4 py-2.5">{d.vices.length > 0 && <Badge tone="rose"><AlertTriangle size={12} className="mr-1 inline" />{d.vices.length} vice(s)</Badge>}</td>
                <td className="px-4 py-2.5 text-slate-500">{Math.round(d.anciennete_jours / 30)} mois</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

function DossierPage() {
  const { id } = useParams()
  const [d, setD] = useState<DossierDetail | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => { if (id) api.dossier(id).then(setD).catch((e) => setError(e.message)) }, [id])

  if (error) return <ErrorBox message={error} />
  if (!d) return <Spinner label="Calcul du score…" />
  const n = d.dossier.notification
  const total = d.conciliation.montant_notifie
  const maxImpact = Math.max(...d.score.explications.map((e) => Math.abs(e.impact)), 0.01)
  const vices = d.procedure.filter((p) => p.statut === 'vice')
  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/administration')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-navy-900"><ArrowLeft size={14} /> Retour au stock</button>
      <Card tone="dark">
        <div className="text-xs uppercase tracking-wide text-gold">{n.centre} · {d.dossier.etape}</div>
        <div className="text-xl font-semibold">{n.entreprise.nom}</div>
        <div className="text-sm text-slate-300">{n.reference} · notifiée le {frDate(n.date_notification)} · {n.entreprise.secteur} · {n.entreprise.gouvernorat} · {n.chefs.length} chef(s) · {dt(total)}</div>
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
                <div className="mt-1 h-2 rounded-full bg-slate-100">
                  <div className={clsx('h-2 rounded-full', e.impact < 0 ? 'bg-rose-400' : 'bg-emerald-400')} style={{ width: `${(Math.abs(e.impact) / maxImpact) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
          {vices.length > 0 && (
            <div className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">
              <b>Vice(s) de procédure :</b> {vices.map((v) => v.detail).join(' ')}
            </div>
          )}
        </Card>
      </div>

      <Card className="overflow-x-auto">
        <SectionTitle sub={d.conciliation.commentaire}>Proposition de conciliation</SectionTitle>
        <table className="w-full text-sm">
          <thead className="whitespace-nowrap text-left text-xs uppercase text-slate-500">
            <tr><th className="py-2">Chef</th><th className="py-2 text-right">Notifié</th><th className="py-2 text-right">P(maintenu)</th><th className="py-2">Recommandation</th><th className="py-2 text-right">Proposé</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {d.conciliation.items.map((it) => (
              <tr key={it.chef_id}>
                <td className="py-2.5 pr-4"><div className="font-medium">{it.chef_id} · {it.libelle}</div><div className="text-xs text-slate-500">{it.justification}</div></td>
                <td className="whitespace-nowrap py-2.5 text-right">{dt(it.montant)}</td>
                <td className="py-2.5 text-right">{Math.round(it.p_maintenu * 100)} %</td>
                <td className="py-2.5"><Badge tone={it.action === 'maintenir' ? 'emerald' : it.action === 'transiger' ? 'amber' : 'rose'}>{it.action}</Badge></td>
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
        <p className="mt-3 text-xs text-slate-500">Recommandation de l'IA : la décision revient à l'agent habilité. Chaque recommandation est tracée dans le journal.</p>
      </Card>
    </div>
  )
}

function Controle() {
  const input = useRef<HTMLInputElement>(null)
  const [a, setA] = useState<Analyse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async (f: File) => {
    setBusy(true); setError(''); setA(null)
    try { setA(await api.analyser(f, '/api/admin/controle-qualite')) } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-6">
      <Card>
        <SectionTitle sub="Le vérificateur dépose son projet de notification : JISER signale les vices de procédure et les chefs mal motivés AVANT l'envoi, pour éviter une annulation au tribunal.">Contrôle qualité d'une notification</SectionTitle>
        <div className="flex flex-wrap gap-3">
          <button onClick={() => input.current?.click()} disabled={busy} className="flex items-center gap-2 rounded-xl bg-navy-900 px-5 py-2.5 font-semibold text-white hover:bg-navy-800"><FileUp size={16} /> Déposer un projet de notification</button>
          <button onClick={async () => run(await api.exempleBlob('notification_sami.pdf'))} disabled={busy} className="rounded-xl bg-slate-100 px-4 py-2.5 text-sm hover:bg-slate-200">Tester avec le projet « Sfax »</button>
          <input ref={input} type="file" accept=".pdf,.txt,.png,.jpg,.jpeg" className="hidden" onChange={(e) => e.target.files?.[0] && run(e.target.files[0])} />
        </div>
      </Card>
      {busy && <Spinner label="Contrôle en cours…" />}
      {error && <ErrorBox message={error} />}
      {a && <AnalyseView a={a} mode="controle" />}
    </div>
  )
}

const BAR_COLORS = ['#0b2f5b', '#1d4f8f', '#2f74c0', '#c29a2e', '#d9b85c', '#94a3b8']

function TableauDeBord() {
  const [d, setD] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.dashboard().then(setD).catch((e) => setError(e.message)) }, [])
  if (error) return <ErrorBox message={error} />
  if (!d) return <Spinner label="Chargement du tableau de bord…" />
  const k = d.kpi
  const m = d.modele
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <Kpi label="Montant bloqué en contentieux" value={mdt(k.montant_bloque)} tone="danger" hint={`${k.dossiers_en_cours} dossiers en cours`} />
        <Kpi label="Recouvrable estimé" value={mdt(k.montant_recouvrable_estime)} tone="success" />
        <Kpi label="Dossiers avec vice de procédure" value={k.dossiers_avec_vice} tone="warning" hint="Risque d'annulation élevé" />
        <Kpi label="Durée moyenne d'un dossier" value={`${k.duree_moyenne_mois} mois`} hint={`Recouvrement historique : ${Math.round(k.taux_recouvrement_historique * 100)} %`} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle sub="Montant notifié en attente, par gouvernorat">Où l'argent est bloqué</SectionTitle>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={d.par_gouvernorat.slice(0, 12)} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tickFormatter={(v) => `${(v / 1e6).toFixed(0)} M`} />
              <YAxis type="category" dataKey="gouvernorat" width={80} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => mdt(Number(v))} />
              <Bar dataKey="montant" name="Notifié" fill="#0b2f5b" radius={[0, 4, 4, 0]} />
              <Bar dataKey="recouvrable" name="Recouvrable" fill="#c29a2e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <SectionTitle sub={`Sur les dossiers clôturés, ${Math.round(k.taux_chefs_annules * 100)} % des chefs ont été annulés. Principales causes :`}>Pourquoi les redressements tombent</SectionTitle>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={d.causes_annulation} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" />
              <YAxis type="category" dataKey="cause" width={150} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="nb" name="Chefs annulés" radius={[0, 4, 4, 0]}>
                {d.causes_annulation.map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-slate-500">→ Les vices de procédure et les motivations insuffisantes sont évitables : c'est l'objet du contrôle qualité avant envoi.</p>
        </Card>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Montants par type de redressement</SectionTitle>
          <ul className="space-y-2 text-sm">
            {d.par_type.map((t) => (
              <li key={t.type} className="flex justify-between border-b border-slate-100 pb-1.5"><span>{t.type}</span><b>{mdt(t.montant)}</b></li>
            ))}
          </ul>
        </Card>
        {m && (
          <Card>
            <SectionTitle sub={m.note}>Performance du modèle (mesurée)</SectionTitle>
            <div className="grid grid-cols-2 gap-3">
              <Kpi label="AUC par chef" value={m.auc_chef_maintenu} />
              <Kpi label="AUC par dossier" value={m.auc_dossier_recouvre_50pct} />
            </div>
            <div className="mt-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">
              Avec une capacité de traitement de {m.triage.capacite}, le tri JISER recouvre <b>{mdt(m.triage.recouvre_jiser)}</b> contre <b>{mdt(m.triage.recouvre_fifo)}</b> en traitant les dossiers par ancienneté,
              soit <b>+{m.triage.gain_vs_fifo_pct} %</b> (test sur {m.n_dossiers_test} dossiers).
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

export default function Administration() {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Espace administration" title="Piloter le contentieux fiscal"
        subtitle="Trier le stock de dossiers, évaluer leur solidité, proposer des conciliations et contrôler les notifications avant envoi." />
      <TipBanner id="administration" title="Par où commencer ?" steps={[
        'Le stock est trié : les dossiers en haut rapportent le plus. Cliquez pour ouvrir.',
        'Dans un dossier : score de solidité, facteurs explicatifs et proposition de conciliation.',
        "Vérificateurs : utilisez le contrôle qualité avant d'envoyer une notification."]} />
      <div className="flex flex-wrap gap-2 border-b border-slate-200">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end}
            className={({ isActive }) => clsx('-mb-px border-b-2 px-4 py-2 text-sm font-medium', isActive ? 'border-gold text-navy-900' : 'border-transparent text-slate-500 hover:text-navy-900')}>
            {t.label}
          </NavLink>
        ))}
      </div>
      <Routes>
        <Route index element={<Stock />} />
        <Route path="dossier/:id" element={<DossierPage />} />
        <Route path="tableau-de-bord" element={<TableauDeBord />} />
        <Route path="controle-qualite" element={<Controle />} />
      </Routes>
    </div>
  )
}
