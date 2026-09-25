import clsx from 'clsx'
import { AlertTriangle, ArrowRight, CheckCircle2, Clock, Copy, Download, FileText, FileUp, FolderOpen, MessageCircle, PenLine, Sparkles, Wallet } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, dt, frDate, type Analyse, type AnalyseResume, type Reponse, type Session } from '../../api'
import AiPanel from '../../components/AiPanel'
import AnalyseView from '../../components/AnalyseView'
import AssistantChat from '../../components/AssistantChat'
import { Badge, Button, Card, ErrorBox, SectionTitle, Spinner, TipBanner } from '../../components/ui'

export const langueOf = (s: Session): 'fr' | 'derja' => (s.utilisateur?.langue === 'derja' ? 'derja' : 'fr')

function Title({ title, sub, actions }: { title: string; sub: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-3xl font-bold text-navy-900">{title}</h1><p className="mt-1 text-slate-500">{sub}</p></div>
      {actions}
    </div>
  )
}

function DeadlineBadge({ jours }: { jours: number }) {
  return <Badge tone={jours < 0 ? 'slate' : jours <= 7 ? 'rose' : jours <= 15 ? 'amber' : 'emerald'}>
    <Clock size={12} className="mr-1" />{jours < 0 ? 'Délai dépassé' : `J-${jours}`}
  </Badge>
}

// ---- Tableau de bord ------------------------------------------------------------------------

export function EntrepriseDashboard({ session }: { session: Session }) {
  const [rows, setRows] = useState<AnalyseResume[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.analyses().then(setRows).catch((e) => setError(e.message)) }, [])
  const u = session.utilisateur
  const next = rows?.filter((r) => r.jours_restants >= 0).sort((a, b) => a.jours_restants - b.jours_restants)[0]
  const derja = langueOf(session) === 'derja'

  return (
    <div className="space-y-6">
      <Title title={derja ? `Ahla ${u?.prenom ?? ''} 👋` : `Bonjour ${u?.prenom ?? ''} 👋`}
        sub={derja ? 'Houni tetba3 notifications mte3ek, el délais w les réponses.' : 'Suivez vos notifications, vos délais et vos réponses.'}
        actions={<Link to="/entreprise/analyser"><Button variant="gold"><FileUp size={16} /> Analyser une notification</Button></Link>} />
      <TipBanner id="entreprise-dashboard" title="Votre parcours" steps={[
        'Déposez la notification reçue : JISER l\'analyse chef par chef.',
        'Posez vos questions à l\'assistant IA, en français ou en tounsi.',
        'Générez le brouillon de réponse et envoyez-le avant la date limite.']} />
      {error && <ErrorBox message={error} />}
      {!rows ? <Spinner label="Chargement…" /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { icon: FolderOpen, label: 'Notifications analysées', value: String(rows.length), tint: 'bg-bridge-light text-bridge' },
              { icon: Wallet, label: 'Montant réclamé', value: dt(rows.reduce((s, r) => s + Number(r.montant_total), 0)), tint: 'bg-gold-light text-gold-dark' },
              { icon: CheckCircle2, label: 'Montant contestable estimé', value: dt(rows.reduce((s, r) => s + Number(r.montant_contestable), 0)), tint: 'bg-emerald-50 text-emerald-600' },
              { icon: Clock, label: 'Prochaine échéance', value: next ? frDate(next.date_limite) : '—', tint: 'bg-rose-50 text-rose-500', hint: next ? `J-${next.jours_restants} · ${next.reference}` : 'Aucune' },
            ].map(({ icon: Icon, label, value, tint, hint }) => (
              <Card key={label} className="p-5">
                <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${tint}`}><Icon size={22} /></div>
                <div className="mt-4 text-sm text-slate-500">{label}</div>
                <div className="mt-1 font-display text-2xl font-bold text-navy-900">{value}</div>
                {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
              </Card>
            ))}
          </div>
          {rows.length === 0 ? (
            <Card className="py-12 text-center">
              <FileText className="mx-auto text-slate-300" size={48} />
              <p className="mt-3 font-semibold text-navy-900">Aucune notification pour le moment</p>
              <p className="text-sm text-slate-500">Déposez votre première notification de redressement pour commencer.</p>
              <Link to="/entreprise/analyser" className="mt-4 inline-block"><Button variant="gold">Analyser une notification <ArrowRight size={16} /></Button></Link>
            </Card>
          ) : <DossiersList rows={rows.slice(0, 5)} title="Mes derniers dossiers" />}
        </>
      )}
    </div>
  )
}

function DossiersList({ rows, title }: { rows: AnalyseResume[]; title: string }) {
  const navigate = useNavigate()
  return (
    <Card className="overflow-x-auto p-0">
      <div className="p-5 pb-2"><SectionTitle>{title}</SectionTitle></div>
      <table className="w-full text-sm">
        <thead className="whitespace-nowrap bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr><th className="px-5 py-2">Notification</th><th className="px-5 py-2 text-right">Réclamé</th><th className="px-5 py-2 text-right">Contestable</th><th className="px-5 py-2">Procédure</th><th className="px-5 py-2">Date limite</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r.id} onClick={() => navigate(`/entreprise/dossiers/${r.id}`)} className="cursor-pointer hover:bg-gold-light/40">
              <td className="px-5 py-3"><div className="font-medium text-navy-900">{r.reference}</div><div className="text-xs text-slate-500">{r.entreprise} · analysée le {frDate(r.cree_le)}</div></td>
              <td className="whitespace-nowrap px-5 py-3 text-right">{dt(Number(r.montant_total))}</td>
              <td className="whitespace-nowrap px-5 py-3 text-right font-semibold text-gold-dark">{dt(Number(r.montant_contestable))}</td>
              <td className="px-5 py-3">{r.nb_vices > 0 ? <Badge tone="rose"><AlertTriangle size={12} className="mr-1" />{r.nb_vices} vice(s)</Badge> : <Badge tone="emerald">Régulière</Badge>}</td>
              <td className="whitespace-nowrap px-5 py-3"><span className="mr-2">{frDate(r.date_limite)}</span><DeadlineBadge jours={r.jours_restants} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

export function MesDossiers() {
  const [rows, setRows] = useState<AnalyseResume[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.analyses().then(setRows).catch((e) => setError(e.message)) }, [])
  return (
    <div className="space-y-6">
      <Title title="Mes dossiers" sub="Toutes les notifications que vous avez analysées." actions={<Link to="/entreprise/analyser"><Button variant="gold"><FileUp size={16} /> Nouvelle analyse</Button></Link>} />
      {error && <ErrorBox message={error} />}
      {!rows ? <Spinner /> : rows.length === 0 ? <Card className="text-center text-slate-500">Aucun dossier pour le moment.</Card> : <DossiersList rows={rows} title={`${rows.length} dossier(s)`} />}
    </div>
  )
}

// ---- Nouvelle analyse -----------------------------------------------------------------------

const STEPS = ['Lecture du document', 'Extraction des chefs de redressement', 'Contrôle de la procédure (CDPF)', 'Recherche des articles de loi',
  'Évaluation par le modèle ML', 'Explications par l\'IA']

export function Analyser({ session }: { session: Session }) {
  const input = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)
  const [step, setStep] = useState(-1)
  const [error, setError] = useState('')
  const [samples, setSamples] = useState<{ nom: string; fichier: string }[]>([])
  const navigate = useNavigate()
  useEffect(() => { api.exemples().then(setSamples).catch(() => setSamples([])) }, [])

  const run = async (file: File) => {
    setError(''); setStep(0)
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 500)
    try {
      const [r] = await Promise.all([api.analyser(file, langueOf(session)), new Promise((res) => setTimeout(res, 2500))])
      navigate(`/entreprise/dossiers/${(r as Analyse).analyse_id}`)
    } catch (e) { setError((e as Error).message); setStep(-1) } finally { clearInterval(timer) }
  }

  return (
    <div className="space-y-6">
      <Title title="Analyser une notification" sub="PDF, photo ou texte. L'IA lit le document, contrôle la procédure et explique chaque chef de redressement." />
      {step < 0 ? (
        <Card className="p-8">
          <div onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) void run(e.dataTransfer.files[0]) }}
            onClick={() => input.current?.click()}
            className={clsx('cursor-pointer rounded-2xl border-2 border-dashed p-14 text-center transition', drag ? 'border-gold bg-gold-light/40' : 'border-slate-300 hover:border-gold hover:bg-canvas')}>
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-900 text-white"><FileUp size={30} /></div>
            <p className="mt-4 text-lg font-semibold text-navy-900">Déposez votre notification de redressement</p>
            <p className="text-sm text-slate-500">ou cliquez pour choisir un fichier · PDF, JPG, PNG, TXT</p>
            <p className="mt-3 inline-flex items-center gap-1 rounded-full bg-gold-light px-3 py-1 text-xs text-gold-dark"><Sparkles size={12} /> Les photos de notifications sont lues par l'IA</p>
            <input ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt" className="hidden" onChange={(e) => e.target.files?.[0] && run(e.target.files[0])} />
          </div>
          {samples.length > 0 && (
            <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
              <span className="text-slate-500">Exemples :</span>
              {samples.map((s) => (
                <button key={s.fichier} onClick={async () => run(await api.exempleBlob(s.fichier))}
                  className="flex items-center gap-1.5 rounded-lg bg-gold-light px-3 py-1.5 font-medium text-navy-900 ring-1 ring-gold/40 hover:bg-gold hover:text-white">
                  <FileText size={14} /> {s.nom === 'notification_sami' ? 'Distribution El Amen (Sfax)' : 'Textile Jasmin (Monastir)'}
                </button>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <Card className="mx-auto max-w-xl">
          <ul className="space-y-3">
            {STEPS.map((s, i) => (
              <li key={s} className="flex items-center gap-3 text-sm">
                {i < step ? <CheckCircle2 className="text-emerald-500" size={18} />
                  : i === step ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-gold" />
                    : <div className="h-4 w-4 rounded-full border-2 border-slate-200" />}
                <span className={i <= step ? 'text-slate-800' : 'text-slate-400'}>{s}</span>
                {s.includes('IA') && <Sparkles size={14} className="text-gold" />}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {error && <ErrorBox message={error} />}
    </div>
  )
}

// ---- Fiche dossier --------------------------------------------------------------------------

export function DossierDetail() {
  const { id } = useParams()
  const [a, setA] = useState<Analyse | null>(null)
  const [error, setError] = useState('')
  const [langBusy, setLangBusy] = useState(false)
  const [lettre, setLettre] = useState('')
  const [draftBusy, setDraftBusy] = useState(false)
  const [signataire, setSignataire] = useState('Le Gérant')
  useEffect(() => { if (id) api.analyse(id).then(setA).catch((e) => setError(e.message)) }, [id])

  const switchLang = async (l: 'fr' | 'derja') => {
    if (!id || !a || a.langue === l) return
    setLangBusy(true)
    try { setA(await api.analyse(id, l)) } catch (e) { setError((e as Error).message) } finally { setLangBusy(false) }
  }
  const draft = async () => {
    if (!id) return
    setDraftBusy(true)
    try { setLettre((await api.brouillon(id, signataire)).lettre) } catch (e) { setError((e as Error).message) } finally { setDraftBusy(false) }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([lettre], { type: 'text/plain;charset=utf-8' }))
    const el = document.createElement('a'); el.href = url; el.download = `reponse_${a?.notification.reference}.txt`; el.click()
    URL.revokeObjectURL(url)
  }

  if (error) return <ErrorBox message={error} />
  if (!a) return <Spinner label="Chargement de l'analyse…" />
  return (
    <div className="grid gap-6 2xl:grid-cols-3">
      <div className="space-y-6 2xl:col-span-2">
        <Link to="/entreprise/dossiers" className="text-sm text-slate-500 hover:text-navy-900">← Mes dossiers</Link>
        <AnalyseView a={a} onLangue={switchLang} langueBusy={langBusy} />
        <AiPanel title="Brouillon de réponse (article 44 du CDPF)" mode={lettre ? (a.mode) : undefined} loading={draftBusy}>
          {!lettre ? (
            <div className="flex flex-wrap items-center gap-3">
              <input value={signataire} onChange={(e) => setSignataire(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Signataire" />
              <Button variant="gold" onClick={draft}><PenLine size={16} /> Rédiger ma réponse</Button>
              <span className="text-xs text-slate-500">La lettre officielle est rédigée en français.</span>
            </div>
          ) : (
            <>
              <textarea value={lettre} onChange={(e) => setLettre(e.target.value)} rows={22} className="w-full rounded-xl border border-slate-300 bg-white p-4 font-mono text-xs leading-relaxed" />
              <div className="mt-3 flex gap-2">
                <Button variant="light" onClick={() => navigator.clipboard.writeText(lettre)}><Copy size={14} /> Copier</Button>
                <Button variant="light" onClick={download}><Download size={14} /> Télécharger</Button>
              </div>
            </>
          )}
        </AiPanel>
      </div>
      <div className="space-y-3">
        <div className="flex items-center gap-2 pt-7 font-semibold text-navy-900"><MessageCircle size={18} className="text-gold" /> Questions sur ce dossier</div>
        <div className="2xl:sticky 2xl:top-6"><AssistantChat langue={a.langue} analyseId={id} compact /></div>
      </div>
    </div>
  )
}

// ---- Assistant et réponses ------------------------------------------------------------------

export function Assistant({ session }: { session: Session }) {
  const [langue, setLangue] = useState<'fr' | 'derja'>(langueOf(session))
  const [rows, setRows] = useState<AnalyseResume[]>([])
  const [ctx, setCtx] = useState('')
  useEffect(() => { api.analyses().then(setRows).catch(() => setRows([])) }, [])
  return (
    <div className="space-y-6">
      <Title title="Assistant fiscal IA" sub="Posez vos questions en français ou en tounsi. L'assistant s'appuie sur les textes de loi et cite ses sources."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {rows.length > 0 && (
              <select value={ctx} onChange={(e) => setCtx(e.target.value)} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="">Sans dossier</option>
                {rows.map((r) => <option key={r.id} value={r.id}>Dossier {r.reference}</option>)}
              </select>
            )}
            <div className="flex rounded-xl bg-white p-1 ring-1 ring-slate-200">
              {(['fr', 'derja'] as const).map((l) => (
                <button key={l} onClick={() => setLangue(l)} className={clsx('rounded-lg px-3 py-1.5 text-sm font-medium', langue === l ? 'bg-navy-900 text-white' : 'text-slate-600')}>
                  {l === 'fr' ? 'Français' : 'Tounsi'}
                </button>
              ))}
            </div>
          </div>
        } />
      <AssistantChat key={`${langue}-${ctx}`} langue={langue} analyseId={ctx || undefined} />
    </div>
  )
}

export function MesReponses() {
  const [rows, setRows] = useState<Reponse[] | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  useEffect(() => { api.reponses().then(setRows).catch(() => setRows([])) }, [])
  return (
    <div className="space-y-6">
      <Title title="Mes réponses" sub="Les brouillons de réponse générés pour vos notifications." />
      {!rows ? <Spinner /> : rows.length === 0 ? (
        <Card className="py-10 text-center text-slate-500">Aucun brouillon pour le moment : ouvrez un dossier et cliquez sur « Rédiger ma réponse ».</Card>
      ) : rows.map((r) => (
        <Card key={r.id}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-medium text-navy-900"><FileText size={18} className="text-gold" /> Brouillon du {frDate(r.cree_le)}
              <Badge tone={r.mode === 'ia' ? 'gold' : 'slate'}>{r.mode === 'ia' ? 'Rédigé avec l\'IA' : 'Modèle de lettre'}</Badge></div>
            <div className="flex gap-2">
              <Button variant="light" onClick={() => setOpen(open === r.id ? null : r.id)}>{open === r.id ? 'Masquer' : 'Afficher'}</Button>
              <Button variant="light" onClick={() => navigator.clipboard.writeText(r.lettre)}><Copy size={14} /> Copier</Button>
              <Link to={`/entreprise/dossiers/${r.analyse_id}`}><Button variant="ghost">Dossier</Button></Link>
            </div>
          </div>
          {open === r.id && <pre className="mt-4 whitespace-pre-wrap rounded-xl bg-canvas p-4 text-xs text-slate-700">{r.lettre}</pre>}
        </Card>
      ))}
    </div>
  )
}
