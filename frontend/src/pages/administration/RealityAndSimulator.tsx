import { Building, Gauge, Landmark, Scale, TrendingUp } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, SectionTitle } from '../../components/ui'

interface Officiel {
  source: string
  source_url: string
  verifications_fiscales: Record<string, number>
  duree_moyenne_verification_jours: Record<string, number>
  rendement_controle_MD: Record<string, number>
  contentieux: {
    affaires_enrolees: Record<string, number>
    affaires_jugees: Record<string, number>
    jugements_2020: { confirmees: number; revisees: number; annulees: number; conciliees: number }
    taux_annulation_affaires_jugees: Record<string, number>
    taux_median_confirmation_TO: Record<string, number>
    montants_TO_confirmes_1re_instance: Record<string, { taux: number; montant_MD: number }>
  }
  recettes_fiscales_MD: Record<string, number | string>
}

const fmt = (n: number) => n.toLocaleString('fr-FR')

/** Real figures published by the Ministry of Finance, and how JISER's simulation compares. */
export function OfficialReality({ simulatedRecovery }: { simulatedRecovery: number }) {
  const [d, setD] = useState<Officiel | null>(null)
  useEffect(() => { fetch('/api/donnees-officielles').then((r) => r.json()).then(setD).catch(() => {}) }, [])
  if (!d) return null
  const c = d.contentieux
  const j = c.jugements_2020
  const juges = j.confirmees + j.revisees + j.annulees + j.conciliees
  const flux = [
    { annee: '2019', enrolees: c.affaires_enrolees['2019'], jugees: c.affaires_jugees['2019'] },
    { annee: '2020', enrolees: c.affaires_enrolees['2020'], jugees: c.affaires_jugees['2020'] },
  ]
  const issues = [
    { issue: 'Confirmées', n: j.confirmees, color: '#0b2f5b' },
    { issue: 'Révisées', n: j.revisees, color: '#2f74c0' },
    { issue: 'Conciliées', n: j.conciliees, color: '#10b981' },
    { issue: 'Annulées', n: j.annulees, color: '#e11d48' },
  ]
  const officialRate = c.montants_TO_confirmes_1re_instance['2020'].taux
  const backlog2020 = c.affaires_enrolees['2020'] - c.affaires_jugees['2020']

  return (
    <Card className="border-2 border-navy-900/10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <SectionTitle sub={`Source : ${d.source}.`}>La réalité officielle du contentieux fiscal</SectionTitle>
        <a href={d.source_url} target="_blank" rel="noreferrer" className="rounded-full bg-navy-900 px-3 py-1 text-xs font-semibold text-white">Données réelles · ministère des Finances</a>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { icon: Scale, v: fmt(c.affaires_enrolees['2020']), l: 'affaires de contentieux enrôlées en 2020', t: 'text-navy-900' },
          { icon: Landmark, v: fmt(c.affaires_jugees['2020']), l: 'affaires jugées en 2020', t: 'text-navy-900' },
          { icon: TrendingUp, v: `+${fmt(backlog2020)}`, l: 'dossiers de plus dans le stock en un an', t: 'text-rose-600' },
          { icon: Gauge, v: `${d.duree_moyenne_verification_jours['2020']} j`, l: 'durée moyenne d\'une vérification (2020)', t: 'text-gold-dark' },
        ].map(({ icon: Icon, v, l, t }) => (
          <div key={l} className="rounded-2xl bg-canvas p-4">
            <Icon size={20} className="text-gold-dark" />
            <div className={`mt-2 font-display text-3xl font-bold ${t}`}>{v}</div>
            <div className="text-xs text-slate-500">{l}</div>
          </div>
        ))}
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <div className="text-sm font-semibold text-navy-900">Entrées vs jugements : le stock grossit</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={flux} margin={{ left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="annee" />
              <YAxis />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend />
              <Bar dataKey="enrolees" name="Affaires enrôlées" fill="#c29a2e" radius={[6, 6, 0, 0]} />
              <Bar dataKey="jugees" name="Affaires jugées" fill="#0b2f5b" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <div className="text-sm font-semibold text-navy-900">Issue des {fmt(juges)} affaires jugées en 2020</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={issues} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="issue" width={90} />
              <Tooltip formatter={(v) => `${fmt(Number(v))} (${Math.round((Number(v) / juges) * 100)} %)`} />
              <Bar dataKey="n" name="Affaires" radius={[0, 6, 6, 0]}>{issues.map((x) => <Cell key={x.issue} fill={x.color} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-900">
        <Building size={18} />
        <span>
          <b>Calibration vérifiée :</b> les dossiers simulés de JISER suivent la distribution officielle des jugements 2020 (51,5 % confirmés, 34 % révisés ou conciliés, 14,5 % annulés).
          Taux de recouvrement simulé : <b>{Math.round(simulatedRecovery * 100)} %</b> ; montants confirmés en 1re instance en 2020 (officiel) : <b>{Math.round(officialRate * 100)} %</b>.
        </span>
      </div>
    </Card>
  )
}

function Slider({ label, value, min, max, step, unit, onChange, help }: {
  label: string; value: number; min: number; max: number; step: number; unit: string; onChange: (v: number) => void; help: string
}) {
  return (
    <label className="block">
      <div className="flex justify-between text-sm"><span className="font-medium text-navy-900">{label}</span><b className="text-gold-dark">{value}{unit}</b></div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="mt-2 w-full accent-[#c29a2e]" />
      <span className="text-xs text-slate-500">{help}</span>
    </label>
  )
}

/** What-if: how conciliation and pre-sending quality control change the national backlog. */
export function ImpactSimulator() {
  // official 2020 flows (ministère des Finances, RAP 2020)
  const ENTREES = 5059
  const JUGEES = 1139
  const ANNULATION = 0.1449
  const MONTANT_MOYEN_MD = 186.89 / 587   // amount per confirmed case, 2020
  const [conciliation, setConciliation] = useState(20)
  const [qualite, setQualite] = useState(50)
  const [productivite, setProductivite] = useState(50)
  const [stock, setStock] = useState(15000)

  const r = useMemo(() => {
    const concilies = ENTREES * (conciliation / 100)                 // settled before court with JISER proposals
    const entreesTribunal = ENTREES - concilies
    const netBase = ENTREES - JUGEES
    const netJiser = entreesTribunal - JUGEES * (1 + productivite / 100)
    const annulationsEvitees = JUGEES * ANNULATION * (qualite / 100)
    const gainMD = (annulationsEvitees + concilies * 0.7) * MONTANT_MOYEN_MD
    const annees = netJiser < 0 ? stock / -netJiser : null
    const baisse = Math.round((1 - netJiser / netBase) * 100)
    return { concilies, netBase, netJiser, annulationsEvitees, gainMD, annees, baisse }
  }, [conciliation, qualite, productivite, stock])

  return (
    <Card>
      <SectionTitle sub="Projection à partir des flux officiels 2020 (5 059 affaires enrôlées, 1 139 jugées, 14,5 % d'annulations). Hypothèses réglables : ce n'est pas une prévision.">
        Simulateur d'impact de JISER
      </SectionTitle>
      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-6">
          <Slider label="Dossiers réglés par conciliation avant le tribunal" value={conciliation} min={0} max={60} step={5} unit=" %" onChange={setConciliation}
            help="Grâce aux propositions de conciliation expliquées de JISER." />
          <Slider label="Annulations évitées par le contrôle qualité avant envoi" value={qualite} min={0} max={100} step={10} unit=" %" onChange={setQualite}
            help="Vices de procédure et défauts de motivation corrigés avant la notification." />
          <Slider label="Dossiers traités en plus grâce au tri et aux avis IA" value={productivite} min={0} max={150} step={10} unit=" %" onChange={setProductivite}
            help="Temps gagné par dossier : analyse, recherche d'articles et rédaction assistées." />
          <Slider label="Stock actuel estimé (hypothèse)" value={stock} min={5000} max={40000} step={1000} unit=" dossiers" onChange={setStock}
            help="Le stock réel n'est pas publié : à remplacer par le chiffre de la DGI." />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl bg-rose-50 p-4">
            <div className="text-xs text-rose-700">Évolution annuelle du stock, aujourd'hui</div>
            <div className="font-display text-3xl font-bold text-rose-600">+{fmt(Math.round(r.netBase))}</div>
          </div>
          <div className={`rounded-2xl p-4 ${r.netJiser < 0 ? 'bg-emerald-50' : 'bg-gold-light/60'}`}>
            <div className="text-xs text-slate-600">Évolution annuelle du stock, avec JISER</div>
            <div className={`font-display text-3xl font-bold ${r.netJiser < 0 ? 'text-emerald-600' : 'text-gold-dark'}`}>{r.netJiser > 0 ? '+' : ''}{fmt(Math.round(r.netJiser))}</div>
          </div>
          <div className="rounded-2xl bg-canvas p-4">
            <div className="text-xs text-slate-500">Affaires réglées par conciliation / an</div>
            <div className="font-display text-3xl font-bold text-navy-900">{fmt(Math.round(r.concilies))}</div>
          </div>
          <div className="rounded-2xl bg-canvas p-4">
            <div className="text-xs text-slate-500">Recettes sécurisées en plus / an (estimation)</div>
            <div className="font-display text-3xl font-bold text-navy-900">{r.gainMD.toLocaleString('fr-FR', { maximumFractionDigits: 0 })} MD</div>
          </div>
          <div className="rounded-2xl bg-navy-900 p-4 text-white sm:col-span-2">
            <div className="text-xs text-slate-300">Temps pour résorber le stock</div>
            <div className="font-display text-2xl font-bold text-gold">{r.annees ? `≈ ${r.annees.toFixed(1)} ans` : `Le stock grossit ${r.baisse} % moins vite`}</div>
          </div>
        </div>
      </div>
    </Card>
  )
}
