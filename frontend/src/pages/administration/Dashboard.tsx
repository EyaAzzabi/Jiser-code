import { FolderOpen, Handshake, Timer, TrendingUp, Wallet, type LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, mdt, type Dashboard as DashboardData, type Synthese } from '../../api'
import AiPanel from '../../components/AiPanel'
import ListenButton from '../../components/ListenButton'
import { Card, ErrorBox, SectionTitle, Spinner } from '../../components/ui'

export const CHART_COLORS = ['#2f74c0', '#c29a2e', '#10b981', '#e11d48', '#8b5cf6', '#0b2f5b', '#f59e0b']

function StatCard({ icon: Icon, label, value, hint, tint }: { icon: LucideIcon; label: string; value: string; hint?: string; tint: string }) {
  return (
    <Card className="p-5">
      <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${tint}`}><Icon size={22} /></div>
      <div className="mt-4 text-sm text-slate-500">{label}</div>
      <div className="mt-1 font-display text-2xl font-bold text-navy-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </Card>
  )
}

export default function Dashboard() {
  const [d, setD] = useState<DashboardData | null>(null)
  const [ai, setAi] = useState<Synthese | null>(null)
  const [aiLoading, setAiLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAi = () => {
    setAiLoading(true)
    api.syntheseIA().then(setAi).catch(() => setAi(null)).finally(() => setAiLoading(false))
  }
  useEffect(() => {
    api.dashboard().then(setD).catch((e) => setError(e.message))
    loadAi()
  }, [])

  if (error) return <ErrorBox message={error} />
  if (!d) return <Spinner label="Chargement du tableau de bord…" />
  const k = d.kpi
  const totalMotifs = d.motifs.reduce((s, m) => s + m.nb, 0) || 1

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-navy-900">Tableau de bord de pilotage</h1>
        <p className="mt-1 text-slate-500">Vue d'ensemble du contentieux fiscal et recommandations de l'IA.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={Wallet} label="Montant total bloqué" value={mdt(k.montant_bloque)} hint={`dont ${mdt(k.montant_recouvrable_estime)} recouvrables`} tint="bg-gold-light text-gold-dark" />
        <StatCard icon={FolderOpen} label="Dossiers actifs" value={String(k.dossiers_en_cours)} hint={`${k.dossiers_avec_vice} avec vice de procédure`} tint="bg-bridge-light text-bridge" />
        <StatCard icon={Handshake} label="Taux de conciliation" value={`${Math.round(k.taux_conciliation * 100)} %`} hint="des dossiers clôturés" tint="bg-emerald-50 text-emerald-600" />
        <StatCard icon={Timer} label="Durée moyenne" value={`${Math.round(k.duree_moyenne_mois)} mois`} hint="de la notification à la décision" tint="bg-rose-50 text-rose-500" />
      </div>

      <AiPanel title="Synthèse du stock et actions recommandées" mode={ai?.mode} loading={aiLoading} onRefresh={loadAi}>
        {ai && (
          <div className="grid gap-5 lg:grid-cols-5">
            <div className="flex flex-col gap-3 lg:col-span-2">
              <p className="text-sm leading-relaxed text-slate-700">{ai.synthese}</p>
              <div><ListenButton text={ai.synthese} /></div>
            </div>
            <ol className="grid gap-3 sm:grid-cols-3 lg:col-span-3">
              {ai.actions.map((a, i) => (
                <li key={a.titre} className="rounded-xl bg-white p-3 shadow-sm ring-1 ring-slate-100">
                  <div className="flex items-center gap-2 text-sm font-semibold text-navy-900">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs text-white">{i + 1}</span>{a.titre}
                  </div>
                  <p className="mt-1 text-xs text-slate-600">{a.detail}</p>
                </li>
              ))}
            </ol>
          </div>
        )}
      </AiPanel>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <SectionTitle>Dossiers notifiés vs clôturés (12 derniers mois)</SectionTitle>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={d.serie_mensuelle} margin={{ left: -15, right: 10 }}>
              <defs>
                <linearGradient id="gNot" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2f74c0" stopOpacity={0.35} /><stop offset="100%" stopColor="#2f74c0" stopOpacity={0} /></linearGradient>
                <linearGradient id="gClo" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="100%" stopColor="#10b981" stopOpacity={0} /></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="mois" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="notifies" name="Notifiés" stroke="#2f74c0" strokeWidth={2} fill="url(#gNot)" />
              <Area type="monotone" dataKey="clotures" name="Clôturés" stroke="#10b981" strokeWidth={2} fill="url(#gClo)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <SectionTitle>Motifs de redressement</SectionTitle>
          <ResponsiveContainer width="100%" height={190}>
            <PieChart>
              <Pie data={d.motifs} dataKey="nb" nameKey="motif" innerRadius={55} outerRadius={85} paddingAngle={2}>
                {d.motifs.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <ul className="mt-2 space-y-1.5 text-sm">
            {d.motifs.map((m, i) => (
              <li key={m.motif} className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-slate-600"><span className="h-2.5 w-2.5 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />{m.motif}</span>
                <b className="text-navy-900">{Math.round((m.nb / totalMotifs) * 100)} %</b>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <SectionTitle>Montants bloqués par gouvernorat (millions DT)</SectionTitle>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={d.par_gouvernorat.slice(0, 10)} margin={{ left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="gouvernorat" tick={{ fontSize: 11 }} interval={0} />
              <YAxis tickFormatter={(v) => `${(v / 1e6).toFixed(0)}M`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => mdt(Number(v))} />
              <Bar dataKey="montant" name="Bloqué" radius={[8, 8, 0, 0]}>
                {d.par_gouvernorat.slice(0, 10).map((_, i) => <Cell key={i} fill={i < 3 ? '#0b2f5b' : i < 6 ? '#2f74c0' : '#c29a2e'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <SectionTitle sub={`${Math.round(k.taux_chefs_annules * 100)} % des chefs clôturés ont été annulés`}>Pourquoi les redressements tombent</SectionTitle>
          <ul className="space-y-3">
            {d.causes_annulation.map((c, i) => {
              const max = d.causes_annulation[0]?.nb || 1
              return (
                <li key={c.cause} className="text-sm">
                  <div className="flex justify-between"><span className="text-slate-600">{c.cause}</span><b className="text-navy-900">{c.nb}</b></div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full" style={{ width: `${(c.nb / max) * 100}%`, background: CHART_COLORS[i % CHART_COLORS.length] }} /></div>
                </li>
              )
            })}
          </ul>
          <p className="mt-4 text-xs text-slate-500">Vices de procédure et motivations insuffisantes sont évitables grâce au contrôle qualité avant envoi.</p>
        </Card>
      </div>

      {d.modele && (
        <Card className="flex flex-wrap items-center gap-6 bg-gradient-to-r from-navy-900 to-navy-700 text-white" tone="dark">
          <TrendingUp className="text-gold" size={36} />
          <div className="flex-1">
            <div className="font-semibold">Le tri JISER recouvre +{Math.round(d.modele.triage.gain_vs_fifo_pct)} % par rapport au traitement par ancienneté</div>
            <div className="text-sm text-slate-300">À capacité égale ({d.modele.triage.capacite}) : {mdt(d.modele.triage.recouvre_jiser)} contre {mdt(d.modele.triage.recouvre_fifo)} · AUC {d.modele.auc_chef_maintenu} · test sur {d.modele.n_dossiers_test} dossiers historiques.</div>
          </div>
        </Card>
      )}
    </div>
  )
}
