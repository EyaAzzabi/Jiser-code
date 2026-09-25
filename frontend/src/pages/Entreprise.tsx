import { AlertTriangle, CheckCircle2, Clock, Copy, Download, FileText, FileUp, HelpCircle, PenLine, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, articleLabel, dt, frDate, type Analyse, type ChefAnalyse, type ProcedureCheck } from '../api'
import { Badge, Button, Card, ContestBadge, ErrorBox, Kpi, PageHeader, SectionTitle, Spinner, TipBanner } from '../components/ui'

const STEPS = ['Lecture du document', 'Extraction des chefs de redressement', 'Contrôle de la procédure (CDPF)',
  'Recherche des articles de loi', 'Évaluation de chaque chef']

function Uploader({ onFile, busy }: { onFile: (f: File) => void; busy: boolean }) {
  const input = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)
  const [samples, setSamples] = useState<{ nom: string; fichier: string }[]>([])
  useEffect(() => { api.exemples().then(setSamples).catch(() => setSamples([])) }, [])

  return (
    <Card className="p-8">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]) }}
        onClick={() => input.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition ${drag ? 'border-gold bg-gold-light/40' : 'border-slate-300 hover:border-gold hover:bg-canvas'}`}
      >
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-900 text-white"><FileUp size={30} /></div>
        <p className="mt-3 text-lg font-semibold text-navy-900">Déposez votre notification de redressement</p>
        <p className="text-sm text-slate-500">PDF, photo ou texte · analyse en quelques secondes</p>
        <input ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt" className="hidden" disabled={busy}
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      </div>
      {samples.length > 0 && (
        <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Essayer avec un exemple :</span>
          {samples.map((s) => (
            <button key={s.fichier} disabled={busy}
              onClick={async () => onFile(await api.exempleBlob(s.fichier))}
              className="flex items-center gap-1.5 rounded-lg bg-gold-light px-3 py-1.5 font-medium text-navy-900 ring-1 ring-gold/40 hover:bg-gold hover:text-white">
              <FileText size={14} /> {s.nom.replace('notification_', 'Notification ').replace('sami', 'Sami (Sfax)').replace('jasmin', 'Textile Jasmin (Monastir)')}
            </button>
          ))}
        </div>
      )}
    </Card>
  )
}

function Progress({ step }: { step: number }) {
  return (
    <Card>
      <ul className="space-y-3">
        {STEPS.map((s, i) => (
          <li key={s} className="flex items-center gap-3 text-sm">
            {i < step ? <CheckCircle2 className="text-emerald-500" size={18} />
              : i === step ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-sky-500" />
                : <div className="h-4 w-4 rounded-full border-2 border-slate-200" />}
            <span className={i <= step ? 'text-slate-800' : 'text-slate-400'}>{s}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function ProcedureList({ checks }: { checks: ProcedureCheck[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {checks.map((c) => (
        <li key={c.code} className="flex gap-3 py-2.5 text-sm">
          {c.statut === 'ok' ? <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-500" size={18} />
            : c.statut === 'vice' ? <AlertTriangle className="mt-0.5 shrink-0 text-rose-500" size={18} />
              : <HelpCircle className="mt-0.5 shrink-0 text-amber-500" size={18} />}
          <div>
            <div className="font-medium text-slate-800">{c.label} <span className="text-xs font-normal text-slate-400">· {articleLabel(c.article)}</span></div>
            <div className={c.statut === 'vice' ? 'text-rose-700' : 'text-slate-500'}>{c.detail}</div>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ChefCard({ ca }: { ca: ChefAnalyse }) {
  const [open, setOpen] = useState<string | null>(null)
  const c = ca.chef
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-slate-400">CHEF {c.id.replace('C', 'N°')} · {c.impot} · exercice {c.exercice}</div>
          <h3 className="mt-1 font-semibold text-navy-900">{c.libelle}</h3>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold text-navy-900">{dt(c.montant_principal + c.penalites)}</div>
          <div className="text-xs text-slate-500">dont {dt(c.penalites)} de pénalités</div>
        </div>
      </div>
      <div className="mt-3"><ContestBadge value={ca.contestabilite} /></div>
      <p className="mt-3 rounded-xl bg-bridge-light p-3 text-sm text-slate-700"><span className="font-semibold text-navy-900">En clair : </span>{ca.explication}</p>
      {c.motivation && <p className="mt-2 text-xs italic text-slate-500">Motivation de l'administration : « {c.motivation} »</p>}
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <div className="text-sm font-semibold text-slate-700">Arguments de réponse</div>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-600">{ca.arguments.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-700">Pièces à rassembler</div>
          <ul className="mt-1 space-y-1 text-sm text-slate-600">{ca.pieces_a_fournir.map((p) => <li key={p}>☐ {p}</li>)}</ul>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {ca.articles.map((a) => (
          <button key={a.id} onClick={() => setOpen(open === a.id ? null : a.id)}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium ring-1 ${open === a.id ? 'bg-navy-900 text-white ring-navy-900' : 'bg-white text-navy-800 ring-slate-300 hover:ring-gold'}`}>
            {articleLabel(a.id)}
          </button>
        ))}
      </div>
      {open && (() => {
        const a = ca.articles.find((x) => x.id === open)!
        return (
          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
            {a.extrait}
            <a href={a.source_url} target="_blank" rel="noreferrer" className="mt-1 block text-navy-800 underline decoration-gold">Source : Jurisite Tunisie</a>
          </div>
        )
      })()}
    </Card>
  )
}

function Draft({ analyse }: { analyse: Analyse }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [signataire, setSignataire] = useState('Le Gérant')

  const generate = async () => {
    setBusy(true); setError('')
    try { setText((await api.brouillon(analyse, signataire)).lettre) } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
    const a = document.createElement('a'); a.href = url; a.download = `reponse_${analyse.notification.reference}.txt`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Card>
      <SectionTitle sub="Lettre d'opposition (article 44 du CDPF), à relire par un professionnel avant envoi.">Brouillon de réponse</SectionTitle>
      {!text ? (
        <div className="flex flex-wrap items-center gap-3">
          <input value={signataire} onChange={(e) => setSignataire(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Signataire" />
          <button onClick={generate} disabled={busy} className="flex items-center gap-2 rounded-xl bg-gold px-5 py-2.5 font-semibold text-white hover:bg-gold-dark disabled:opacity-50">
            <PenLine size={16} /> {busy ? 'Rédaction…' : 'Générer le brouillon'}
          </button>
        </div>
      ) : (
        <>
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={22}
            className="w-full rounded-xl border border-slate-300 p-4 font-mono text-xs leading-relaxed" />
          <div className="mt-3 flex gap-2">
            <button onClick={() => navigator.clipboard.writeText(text)} className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm hover:bg-slate-200"><Copy size={14} /> Copier</button>
            <button onClick={download} className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm hover:bg-slate-200"><Download size={14} /> Télécharger</button>
          </div>
        </>
      )}
      {error && <div className="mt-3"><ErrorBox message={error} /></div>}
    </Card>
  )
}

export function AnalyseView({ a, mode = 'entreprise' }: { a: Analyse; mode?: 'entreprise' | 'controle' }) {
  const n = a.notification
  const vices = a.procedure.filter((p) => p.statut === 'vice').length
  return (
    <div className="space-y-6">
      <Card tone="dark">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-xs uppercase tracking-wide text-gold">{n.centre}</div>
            <div className="text-xl font-semibold">{n.entreprise.nom}</div>
            <div className="text-sm text-slate-300">Notification {n.reference} du {frDate(n.date_notification)} · vérification {n.type_verification} · exercices {n.exercices_verifies.join(', ')}</div>
          </div>
          <Badge tone={a.mode === 'ia' ? 'emerald' : 'gold'}>{a.mode === 'ia' ? <><Sparkles size={12} className="mr-1 inline" />Analyse IA</> : 'Analyse hors ligne (règles + modèle)'}</Badge>
        </div>
        <p className="mt-4 rounded-xl bg-white/10 p-3 text-sm">{a.resume}</p>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Kpi label="Montant réclamé" value={dt(a.montant_total)} />
        <Kpi label="Montant contestable estimé" value={dt(a.montant_contestable)} tone="warning" hint="Selon le modèle et les règles du CDPF" />
        {mode === 'entreprise'
          ? <Kpi label="Date limite de réponse" value={frDate(a.date_limite_reponse)} tone={a.jours_restants <= 7 ? 'danger' : 'default'}
            hint={<span className="flex items-center gap-1"><Clock size={12} /> {a.jours_restants >= 0 ? `Il reste ${a.jours_restants} jours` : 'Délai dépassé'}</span>} />
          : <Kpi label="Chefs fragiles" value={`${a.chefs.filter((c) => c.contestabilite !== 'solide').length} / ${a.chefs.length}`} tone="warning" />}
        <Kpi label="Vices de procédure" value={vices} tone={vices ? 'danger' : 'success'} hint={vices ? 'Voir le contrôle ci-dessous' : 'Procédure régulière'} />
      </div>

      <Card>
        <SectionTitle sub="Chaque point est vérifié par rapport au Code des droits et procédures fiscaux.">Contrôle de la procédure</SectionTitle>
        <ProcedureList checks={a.procedure} />
      </Card>

      <div>
        <SectionTitle sub={mode === 'entreprise' ? 'Ce qu\'on vous reproche, et ce que vous pouvez répondre.' : 'Points faibles à renforcer avant envoi.'}>Chefs de redressement</SectionTitle>
        <div className="space-y-4">{a.chefs.map((ca) => <ChefCard key={ca.chef.id} ca={ca} />)}</div>
      </div>

      {mode === 'entreprise' && <Draft analyse={a} />}
    </div>
  )
}

export default function Entreprise() {
  const [analyse, setAnalyse] = useState<Analyse | null>(null)
  const [step, setStep] = useState(-1)
  const [error, setError] = useState('')

  const run = async (file: File) => {
    setError(''); setAnalyse(null); setStep(0)
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 450)
    try {
      const [result] = await Promise.all([api.analyser(file), new Promise((r) => setTimeout(r, 2200))])
      setAnalyse(result as Analyse)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      clearInterval(timer); setStep(-1)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Espace entreprise" title="Comprendre et répondre à votre notification"
        subtitle="Déposez la notification de redressement reçue : JISER l'explique chef par chef, vérifie la procédure et prépare votre réponse."
        actions={analyse && <Button variant="ghost" onClick={() => setAnalyse(null)}>Nouvelle notification</Button>} />
      {!analyse && <TipBanner id="entreprise" title="Comment ça marche ?" steps={[
        "Déposez votre notification (PDF, photo) ou essayez l'exemple de Sami.",
        "Lisez l'analyse : ce qu'on vous reproche, ce qui est contestable, les articles de loi.",
        'Générez le brouillon de réponse et faites-le relire avant la date limite.']} />}
      {!analyse && step < 0 && <Uploader onFile={run} busy={step >= 0} />}
      {step >= 0 && <Progress step={step} />}
      {error && <ErrorBox message={error} />}
      {analyse && <AnalyseView a={analyse} />}
      {step >= 0 && <Spinner label="Analyse en cours…" />}
    </div>
  )
}
