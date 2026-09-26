import clsx from 'clsx'
import { AlertTriangle, BrainCircuit, CheckCircle2, Clock, Download, FileDiff, FlaskConical, GitCompare, Play, RefreshCw, Search, ShieldCheck, ThumbsDown, ThumbsUp, Upload } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { veilleApi, type ChangementVeille, type EtatVeille } from '../../api'
import { Badge, Button, Card, ErrorBox, SectionTitle, Spinner } from '../../components/ui'

const ETAPES = [
  { icon: Download, t: 'Collecte', d: 'Sources officielles téléchargées' },
  { icon: Search, t: 'Détection', d: 'Empreinte SHA-256 de chaque source' },
  { icon: FileDiff, t: 'Découpage', d: 'Article par article' },
  { icon: GitCompare, t: 'Comparaison', d: 'Ajouts, modifications, abrogations' },
  { icon: ShieldCheck, t: 'Validation', d: 'Un juriste approuve chaque changement' },
  { icon: Upload, t: 'Publication', d: 'Version précédente archivée' },
  { icon: BrainCircuit, t: 'Embeddings', d: 'Recalculés pour la recherche IA' },
]
const STATUT: Record<string, { l: string; tone: 'emerald' | 'amber' | 'rose' | 'slate' }> = {
  inchange: { l: 'Inchangée', tone: 'emerald' }, a_jour: { l: 'À jour', tone: 'emerald' }, identique: { l: 'Identique', tone: 'emerald' },
  changements_a_valider: { l: 'Changements à valider', tone: 'amber' }, modifie: { l: 'Modifiée', tone: 'amber' }, erreur: { l: 'Injoignable', tone: 'rose' },
}
const date = (iso?: string | null) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—')

/** Word-level diff: removed words in red, added words in green. */
function Diff({ ancien, nouveau }: { ancien: string; nouveau: string }) {
  const a = ancien.split(/\s+/).slice(0, 400)
  const b = nouveau.split(/\s+/).slice(0, 400)
  const dp = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--)
    dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
  const out: { t: string; k: 'eq' | 'del' | 'add' }[] = []
  let i = 0, j = 0
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { out.push({ t: a[i], k: 'eq' }); i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ t: a[i++], k: 'del' })
    else out.push({ t: b[j++], k: 'add' })
  }
  while (i < a.length) out.push({ t: a[i++], k: 'del' })
  while (j < b.length) out.push({ t: b[j++], k: 'add' })
  return (
    <p className="text-sm leading-relaxed">
      {out.map((w, n) => <span key={n} className={clsx(w.k === 'del' && 'bg-rose-100 text-rose-700 line-through', w.k === 'add' && 'bg-emerald-100 text-emerald-800')}>{w.t} </span>)}
    </p>
  )
}

function Changement({ c, onDecide }: { c: ChangementVeille; onDecide: (c: ChangementVeille, d: 'valide' | 'rejete') => void }) {
  const [ouvert, setOuvert] = useState(false)
  return (
    <li className="rounded-2xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-navy-900">{c.code.toUpperCase()} · article {c.article}</span>
        <Badge tone={c.type === 'ajout' ? 'emerald' : c.type === 'abrogation' ? 'rose' : 'amber'}>{c.type}</Badge>
        {c.simulation && <Badge tone="sky"><FlaskConical size={12} className="mr-1" />simulation</Badge>}
        <span className="text-xs text-slate-500">détecté le {date(c.detecte_le)}</span>
        <div className="ml-auto flex gap-2">
          <button onClick={() => setOuvert(!ouvert)} className="text-xs font-medium text-navy-900 underline decoration-gold underline-offset-4">{ouvert ? 'Masquer' : 'Voir les différences'}</button>
          <Button variant="gold" onClick={() => onDecide(c, 'valide')}><ThumbsUp size={14} /> Publier</Button>
          <Button variant="ghost" onClick={() => onDecide(c, 'rejete')}><ThumbsDown size={14} /> Rejeter</Button>
        </div>
      </div>
      {ouvert && (
        <div className="mt-3 rounded-xl bg-canvas p-3">
          {c.ancien && c.nouveau ? <Diff ancien={c.ancien.text} nouveau={c.nouveau.text} />
            : <p className="text-sm">{(c.nouveau ?? c.ancien)?.text}</p>}
        </div>
      )}
    </li>
  )
}

export default function Veille() {
  const [e, setE] = useState<EtatVeille | null>(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const charger = useCallback(() => veilleApi.etat().then(setE).catch((x) => setError(x.message)), [])
  useEffect(() => { void charger() }, [charger])
  useEffect(() => {   // follow a running pipeline
    if (!e?.en_cours?.debut) return
    const t = setInterval(charger, 3000)
    return () => clearInterval(t)
  }, [e?.en_cours?.debut, charger])

  const action = async (nom: string, f: () => Promise<{ message?: string } | unknown>) => {
    setBusy(nom); setError(''); setMsg('')
    try { const r = await f() as { message?: string }; if (r?.message) setMsg(r.message); await charger() } catch (x) { setError((x as Error).message) } finally { setBusy('') }
  }
  const decider = (c: ChangementVeille, d: 'valide' | 'rejete') => action('decision', () => veilleApi.decider(c.id, d))

  if (!e) return <Spinner />
  const derniere = e.executions[0]
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-navy-900">Veille juridique automatisée</h1>
          <p className="mt-1 max-w-3xl text-slate-500">Les lois changent à chaque loi de finances : JISER surveille les textes officiels chaque semaine, détecte les articles modifiés et met à jour la base de l'IA après validation humaine.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => action('simuler', veilleApi.simuler)} disabled={!!busy}><FlaskConical size={16} /> Simuler un changement</Button>
          <Button variant="gold" onClick={() => action('lancer', veilleApi.lancer)} disabled={!!busy || !!e.en_cours?.debut}><Play size={16} /> Lancer la veille maintenant</Button>
        </div>
      </div>
      {error && <ErrorBox message={error} />}
      {msg && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{msg}</div>}

      <Card>
        <SectionTitle sub="Chaque semaine (planificateur interne ou workflow n8n), ou à la demande.">Le pipeline</SectionTitle>
        <ol className="grid gap-2 sm:grid-cols-4 xl:grid-cols-7">
          {ETAPES.map(({ icon: Icon, t, d }, i) => (
            <li key={t} className={clsx('relative rounded-2xl p-3 text-center', i === 4 ? 'bg-gold-light/70 ring-2 ring-gold' : 'bg-canvas')}>
              <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-gold"><Icon size={18} /></div>
              <div className="mt-2 text-sm font-semibold text-navy-900">{i + 1}. {t}</div><div className="text-xs text-slate-500">{d}</div>
            </li>
          ))}
        </ol>
        {e.en_cours?.debut && (
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-bridge-light p-3 text-sm text-navy-900">
            <RefreshCw size={16} className="animate-spin" /> Exécution en cours : {e.en_cours.etape} · {e.en_cours.source}
          </div>
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Card><div className="text-xs uppercase text-slate-500">Dernière vérification</div><div className="mt-1 font-display text-xl font-bold text-navy-900">{date(derniere?.fin)}</div><div className="text-xs text-slate-500">{derniere?.declencheur ?? 'jamais lancée'}</div></Card>
        <Card><div className="text-xs uppercase text-slate-500">Prochaine exécution</div><div className="mt-1 font-display text-xl font-bold text-navy-900">{date(e.prochaine_execution)}</div><div className="text-xs text-slate-500">hebdomadaire</div></Card>
        <Card><div className="text-xs uppercase text-slate-500">Changements à valider</div><div className={clsx('mt-1 font-display text-3xl font-bold', e.en_attente.length ? 'text-gold-dark' : 'text-emerald-600')}>{e.en_attente.length}</div></Card>
        <Card>
          <div className="text-xs uppercase text-slate-500">Embeddings (recherche IA)</div>
          <div className="mt-1 font-display text-xl font-bold text-navy-900">{e.embeddings.disponible ? `${e.embeddings.articles} articles` : 'non calculés'}</div>
          <div className="text-xs text-slate-500">{e.embeddings.modele ?? '—'} · {date(e.embeddings.calcule_le)}</div>
          <button onClick={() => action('emb', veilleApi.embeddings)} disabled={!!busy} className="mt-2 text-xs font-medium text-navy-900 underline decoration-gold underline-offset-4">{busy === 'emb' ? 'Calcul…' : 'Recalculer'}</button>
        </Card>
      </div>

      <Card className="overflow-x-auto p-0">
        <div className="p-5 pb-2"><SectionTitle>Sources surveillées</SectionTitle></div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-5 py-2">Source</th><th className="px-5 py-2">Articles publiés</th><th className="px-5 py-2">Empreinte</th><th className="px-5 py-2">Vérifiée le</th><th className="px-5 py-2">État</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {e.sources_config.map((s) => {
              const st = e.sources[s.id] ?? {}
              const lab = STATUT[st.statut ?? ''] ?? { l: 'Jamais vérifiée', tone: 'slate' as const }
              return (
                <tr key={s.id}>
                  <td className="px-5 py-3"><div className="font-medium text-navy-900">{s.nom}</div><a href={s.url} target="_blank" rel="noreferrer" className="text-xs text-bridge hover:underline">{s.url.replace(/^https?:\/\//, '').slice(0, 60)}</a></td>
                  <td className="px-5 py-3">{e.base.find((b) => b.code === s.code)?.articles ?? '—'}</td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-500">{st.empreinte ? `${st.empreinte.slice(0, 12)}…` : '—'}</td>
                  <td className="px-5 py-3 text-slate-500">{date(st.verifie_le)}</td>
                  <td className="px-5 py-3"><Badge tone={lab.tone}>{lab.l}</Badge></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>

      <Card>
        <SectionTitle sub="Aucun changement n'atteint l'IA sans validation. Publier archive l'ancienne version et recalcule les embeddings de l'article.">
          <span className="flex items-center gap-2"><AlertTriangle size={18} className="text-gold-dark" /> Changements détectés, à valider par un juriste</span>
        </SectionTitle>
        {e.en_attente.length === 0 ? <p className="flex items-center gap-2 text-sm text-emerald-700"><CheckCircle2 size={16} /> La base juridique est à jour.</p> : (
          <ul className="space-y-3">{e.en_attente.map((c) => <Changement key={c.id} c={c} onDecide={decider} />)}</ul>
        )}
      </Card>

      <Card>
        <SectionTitle>Historique des exécutions</SectionTitle>
        <ul className="divide-y divide-slate-100 text-sm">
          {e.executions.length === 0 && <li className="py-2 text-slate-500">Aucune exécution pour le moment.</li>}
          {e.executions.map((x, i) => (
            <li key={i} className="flex flex-wrap items-center gap-3 py-2.5">
              <Clock size={14} className="text-slate-400" /><span className="text-slate-500">{date(x.fin ?? x.debut)}</span>
              <Badge tone="slate">{x.declencheur}</Badge>
              <span className="flex-1 text-slate-600">{x.resultats.map((r) => `${r.source} : ${STATUT[r.statut]?.l ?? r.statut}${r.changements ? ` (${r.changements})` : ''}`).join(' · ')}</span>
              <b className={x.changements ? 'text-gold-dark' : 'text-emerald-700'}>{x.changements ?? 0} changement(s)</b>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
