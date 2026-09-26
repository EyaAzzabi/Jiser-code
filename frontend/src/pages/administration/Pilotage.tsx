import clsx from 'clsx'
import { Activity, EyeOff, Filter, RotateCcw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { mdt, pilotageApi, type National } from '../../api'
import { Card, ErrorBox, Kpi, PageHeader, SectionTitle, Spinner } from '../../components/ui'
import { ImpactSimulator, OfficialReality } from './RealityAndSimulator'

const PERIODES = [['', 'Toute la période'], ['3', '3 derniers mois'], ['6', '6 derniers mois'], ['12', '12 derniers mois'], ['24', '24 derniers mois']]
const TRANCHES = [['', 'Tous montants'], ['petit', '< 100 000 DT'], ['moyen', '100 000 DT à 1 MDT'], ['gros', '> 1 MDT']]
const pct = (v: number | null) => (v == null ? '—' : `${Math.round(v * 100)} %`)
const REFRESH_S = 10

function Chips({ options, value, onChange }: { options: string[]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => {
        const on = value.includes(o)
        return <button key={o} onClick={() => onChange(on ? value.filter((x) => x !== o) : [...value, o])}
          className={clsx('rounded-full px-2.5 py-1 text-xs font-medium ring-1 transition', on ? 'bg-navy-900 text-white ring-navy-900' : 'bg-white text-slate-600 ring-slate-300 hover:ring-gold')}>{o}</button>
      })}
    </div>
  )
}

/** Minister's view: national, live, anonymous. */
export default function Pilotage() {
  const [gouv, setGouv] = useState<string[]>([])
  const [motifs, setMotifs] = useState<string[]>([])
  const [etape, setEtape] = useState('')
  const [tranche, setTranche] = useState('')
  const [periode, setPeriode] = useState('')
  const [d, setD] = useState<National | null>(null)
  const [maj, setMaj] = useState<number>(0)
  const [now, setNow] = useState(Date.now())
  const [error, setError] = useState('')

  const charger = useCallback(() => {
    const f: Record<string, string> = {}
    if (gouv.length) f.gouvernorats = gouv.join(',')
    if (motifs.length) f.motifs = motifs.join(',')
    if (etape) f.etape = etape
    if (tranche) f.tranche = tranche
    if (periode) f.periode_mois = periode
    return pilotageApi.national(f).then((r) => { setD(r); setMaj(Date.now()) }).catch((e) => setError(e.message))
  }, [gouv, motifs, etape, tranche, periode])

  useEffect(() => { void charger(); const t = setInterval(charger, REFRESH_S * 1000); return () => clearInterval(t) }, [charger])
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t) }, [])
  const reset = () => { setGouv([]); setMotifs([]); setEtape(''); setTranche(''); setPeriode('') }
  const filtres = gouv.length + motifs.length + (etape ? 1 : 0) + (tranche ? 1 : 0) + (periode ? 1 : 0)

  if (error) return <ErrorBox message={error} />
  if (!d) return <Spinner label="Chargement du pilotage national…" />
  const k = d.kpi
  const gouvData = d.par_gouvernorat.map((g) => ({ ...g, montantM: g.montant == null ? 0 : g.montant / 1e6 }))
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Cabinet du ministre · pilotage national" title="Le contentieux fiscal en temps réel"
        subtitle="Statistiques anonymes : aucun nom de contribuable n'est accessible à ce niveau (secret fiscal)."
        actions={<span className="flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />En direct · mis à jour il y a {Math.max(0, Math.round((now - maj) / 1000))} s</span>} />

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold text-navy-900"><Filter size={16} className="text-gold-dark" /> Filtres {filtres > 0 && <span className="rounded-full bg-gold px-2 text-xs text-white">{filtres}</span>}</div>
          {filtres > 0 && <button onClick={reset} className="flex items-center gap-1 text-xs text-slate-500 hover:text-navy-900"><RotateCcw size={12} /> Réinitialiser</button>}
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <label className="text-xs font-medium text-slate-500">Période
            <select value={periode} onChange={(e) => setPeriode(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-navy-900">
              {PERIODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="text-xs font-medium text-slate-500">Montant
            <select value={tranche} onChange={(e) => setTranche(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-navy-900">
              {TRANCHES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="text-xs font-medium text-slate-500">Étape
            <select value={etape} onChange={(e) => setEtape(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-navy-900">
              <option value="">Toutes les étapes</option>{d.options.etapes.map((e) => <option key={e}>{e}</option>)}</select></label>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div><div className="mb-1 text-xs font-medium text-slate-500">Gouvernorats</div><Chips options={d.options.gouvernorats} value={gouv} onChange={setGouv} /></div>
          <div><div className="mb-1 text-xs font-medium text-slate-500">Motif principal du redressement</div><Chips options={d.options.motifs} value={motifs} onChange={setMotifs} /></div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Kpi label="Dossiers en cours" value={k.dossiers_en_cours.toLocaleString('fr-FR')} hint={`${k.dossiers_avec_vice} avec vice de procédure`} />
        <Kpi label="Montant bloqué" value={mdt(k.montant_bloque)} hint={`dont ${mdt(k.montant_recouvrable)} recouvrables (IA)`} tone="warning" />
        <Kpi label="Taux de recouvrement" value={pct(k.taux_recouvrement)} hint={`${k.dossiers_clos.toLocaleString('fr-FR')} dossiers clos`} tone="success" />
        <Kpi label="Durée moyenne" value={k.duree_moyenne_mois == null ? '—' : `${k.duree_moyenne_mois} mois`} hint={`Conciliation ${pct(k.taux_conciliation)} · annulation ${pct(k.taux_annulation)}`} />
      </div>

      <Card tone="dark">
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-2 font-semibold"><Activity size={18} className="text-gold" /> Activité de la plateforme · 24 h</div>
          {([['analyses', 'notifications analysées'], ['messages', 'messages échangés'], ['conciliations', 'décisions de conciliation'], ['questions_ia', 'questions à l\'IA'], ['reponses', 'réponses rédigées']] as const).map(([key, l]) => (
            <div key={key}><div className="font-display text-2xl font-bold text-gold">{d.activite[key]}</div><div className="text-xs text-slate-300">{l}</div></div>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <SectionTitle sub="Montant bloqué par gouvernorat (millions de DT). Groupes de moins de 5 dossiers masqués.">Carte du stock</SectionTitle>
          <ResponsiveContainer width="100%" height={Math.max(260, gouvData.length * 24)}>
            <BarChart data={gouvData} layout="vertical" margin={{ left: 30 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="gouvernorat" width={90} fontSize={11} />
              <Tooltip formatter={(v, _n, p) => ((p.payload as { masque?: boolean }).masque ? 'masqué (< 5 dossiers)' : `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} MDT`)} />
              <Bar dataKey="montantM" name="Montant bloqué" fill="#0b2f5b" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
          {d.par_gouvernorat.some((g) => g.masque) && (
            <p className="mt-2 flex items-center gap-1 text-xs text-slate-500"><EyeOff size={12} /> {d.par_gouvernorat.filter((g) => g.masque).map((g) => g.gouvernorat).join(', ')} : moins de {d.k_anonymat} dossiers, chiffres masqués pour protéger les contribuables.</p>
          )}
        </Card>
        <Card className="xl:col-span-2">
          <SectionTitle sub="Nombre de dossiers en cours par motif principal">Pourquoi on redresse</SectionTitle>
          <ul className="space-y-2">
            {d.par_motif.map((m) => {
              const max = Math.max(...d.par_motif.map((x) => x.nb ?? 0), 1)
              return (
                <li key={m.motif}>
                  <div className="flex justify-between text-sm"><span className="text-slate-700">{m.motif}</span><b className="text-navy-900">{m.masque ? '< 5' : m.nb}</b></div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-gold" style={{ width: `${((m.nb ?? 0) / max) * 100}%` }} /></div>
                </li>
              )
            })}
          </ul>
        </Card>
      </div>

      <Card>
        <SectionTitle sub="Dossiers notifiés (entrées) et clôturés (sorties) par mois">Flux du contentieux</SectionTitle>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={d.flux_mensuel} margin={{ left: -15 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="mois" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Legend />
            <Area type="monotone" dataKey="entrees" name="Entrées" stroke="#c29a2e" fill="#c29a2e" fillOpacity={0.25} />
            <Area type="monotone" dataKey="sorties" name="Sorties" stroke="#0b2f5b" fill="#0b2f5b" fillOpacity={0.15} />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <OfficialReality simulatedRecovery={k.taux_recouvrement ?? 0} />
      <ImpactSimulator />
    </div>
  )
}
