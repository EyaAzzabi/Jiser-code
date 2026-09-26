import clsx from 'clsx'
import { Download, Eye, EyeOff, FileLock2, KeyRound, ScrollText, ShieldCheck, Trash2, UserSearch } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, confidentialiteApi, loadSession, saveSession, type Acces, type AnalyseResume, type ApercuIA, type Traitement } from '../../api'
import { Button, Card, ErrorBox, PageHeader, SectionTitle, Spinner } from '../../components/ui'

const GARANTIES = [
  { icon: FileLock2, t: 'Chiffrement au repos', d: 'Analyses, réponses, messages et justificatifs sont chiffrés (AES + HMAC). La clé ne quitte jamais le serveur.' },
  { icon: EyeOff, t: 'Pseudonymisation avant l\'IA', d: 'Votre nom, votre matricule, vos coordonnées sont remplacés par des jetons avant tout envoi à une IA externe.' },
  { icon: UserSearch, t: 'Accès tracés et limités', d: 'Seul l\'agent de votre centre en charge du dossier y accède ; chaque consultation vous est montrée.' },
  { icon: KeyRound, t: 'Vos droits, en un clic', d: 'Export de toutes vos données, retrait du consentement à l\'IA, suppression de votre compte (loi 2004-63).' },
]

/** Highlight the tokens that replaced identifiers in the text sent to the AI. */
function Surligne({ texte }: { texte: string }) {
  return <>{texte.split(/(\[[A-Z]+_\d+\])/).map((p, i) => /^\[[A-Z]+_\d+\]$/.test(p)
    ? <mark key={i} className="rounded bg-gold-light px-1 font-semibold text-gold-dark">{p}</mark> : <span key={i}>{p}</span>)}</>
}

export default function Confidentialite() {
  const navigate = useNavigate()
  const session = loadSession()
  const [acces, setAcces] = useState<Acces[] | null>(null)
  const [analyses, setAnalyses] = useState<AnalyseResume[]>([])
  const [apercu, setApercu] = useState<ApercuIA | null>(null)
  const [registre, setRegistre] = useState<Traitement[]>([])
  const [ia, setIa] = useState(Boolean(session?.utilisateur?.consentements?.analyse_ia ?? true))
  const [com, setCom] = useState(Boolean(session?.utilisateur?.consentements?.communications ?? false))
  const [confirm, setConfirm] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    confidentialiteApi.acces().then(setAcces).catch((e) => setError(e.message))
    confidentialiteApi.registre().then((r) => setRegistre(r.traitements)).catch(() => {})
    api.analyses().then((a) => { setAnalyses(a); return confidentialiteApi.apercuIA(a[0]?.id) }).then(setApercu).catch(() => {})
  }, [])

  const enregistrer = async (nIa: boolean, nCom: boolean) => {
    setIa(nIa); setCom(nCom); setMsg('')
    try {
      const r = await confidentialiteApi.consentements(nIa, nCom)
      if (session?.utilisateur) saveSession({ ...session, utilisateur: { ...session.utilisateur, consentements: r.consentements } })
      setMsg(nIa ? 'IA générative activée (textes pseudonymisés).' : 'IA générative désactivée : JISER utilise uniquement ses règles et son modèle interne.')
    } catch (e) { setError((e as Error).message) }
  }
  const exporter = async () => {
    try {
      const url = await confidentialiteApi.exporter()
      const a = document.createElement('a'); a.href = url; a.download = 'JISER_mes_donnees.json'; a.click()
    } catch (e) { setError((e as Error).message) }
  }
  const supprimer = async () => {
    try { await confidentialiteApi.supprimer(confirm); saveSession(null); navigate('/') } catch (e) { setError((e as Error).message) }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Loi organique n° 2004-63 · INPDP" title="Confidentialité et mes données"
        subtitle="Vos données fiscales sont protégées à chaque étape. Voici exactement ce que JISER en fait, et vos droits." />
      {error && <ErrorBox message={error} />}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {GARANTIES.map(({ icon: Icon, t, d }) => (
          <Card key={t}><div className="w-fit rounded-xl bg-navy-900 p-2 text-gold"><Icon size={20} /></div>
            <div className="mt-3 font-semibold text-navy-900">{t}</div><p className="mt-1 text-sm text-slate-600">{d}</p></Card>
        ))}
      </div>

      <Card>
        <SectionTitle sub="Aperçu réel, calculé sur vos données : à gauche ce que vous voyez, à droite ce que reçoit l'IA externe.">Ce que voit l'IA</SectionTitle>
        {analyses.length > 1 && (
          <select className="mb-3 rounded-xl border border-slate-300 px-3 py-2 text-sm" onChange={(e) => confidentialiteApi.apercuIA(e.target.value).then(setApercu)}>
            {analyses.map((a) => <option key={a.id} value={a.id}>{a.reference}</option>)}
          </select>
        )}
        {!apercu ? <Spinner /> : (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl bg-canvas p-4 text-sm"><div className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-slate-500"><Eye size={14} /> Vos données</div>{apercu.original}</div>
            <div className="rounded-2xl border-2 border-gold/40 bg-white p-4 text-sm"><div className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-gold-dark"><EyeOff size={14} /> Envoyé à l'IA</div><Surligne texte={apercu.envoye_a_l_ia} /></div>
          </div>
        )}
        {apercu && <p className="mt-3 text-xs text-slate-500">{apercu.remplacements.length} donnée(s) identifiante(s) remplacée(s). Les montants et les articles de loi restent visibles : l'IA en a besoin pour expliquer. Les identifiants sont remis en place uniquement sur votre écran.</p>}
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <SectionTitle sub="Chaque ouverture de vos dossiers par l'administration est enregistrée.">Qui a consulté mes dossiers</SectionTitle>
          {!acces ? <Spinner /> : acces.length === 0 ? <p className="text-sm text-slate-500">Aucune consultation par l'administration pour le moment.</p> : (
            <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto text-sm">
              {acces.map((a, i) => (
                <li key={i} className="flex items-center gap-3 py-2">
                  <ShieldCheck size={16} className="text-gold-dark" />
                  <div className="flex-1"><div className="font-medium text-navy-900">{a.role_label}{a.centre ? ` · CRCI ${a.centre}` : ''}</div>
                    <div className="text-xs text-slate-500">{a.action} · {a.reference}</div></div>
                  <span className="text-xs text-slate-500">{new Date(a.horodatage).toLocaleString('fr-FR')}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <SectionTitle sub="Vous pouvez changer d'avis à tout moment.">Mes consentements</SectionTitle>
          {([['IA générative', 'Explications, assistant et rédaction par une IA externe, sur des textes pseudonymisés. Désactivée, JISER reste utilisable avec ses règles et son modèle interne.', ia, () => enregistrer(!ia, com)],
            ['Informations fiscales', 'Nouveautés fiscales et évolutions de la loi (facultatif).', com, () => enregistrer(ia, !com)]] as const).map(([t, d, on, toggle]) => (
            <div key={t} className="flex items-start gap-4 border-b border-slate-100 py-3 last:border-0">
              <div className="flex-1"><div className="font-medium text-navy-900">{t}</div><div className="text-sm text-slate-500">{d}</div></div>
              <button role="switch" aria-checked={on} aria-label={t} onClick={toggle} className={clsx('relative h-6 w-11 shrink-0 rounded-full transition', on ? 'bg-gold' : 'bg-slate-300')}>
                <span className={clsx('absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition', on ? 'left-5' : 'left-0.5')} />
              </button>
            </div>
          ))}
          {msg && <p className="mt-2 text-sm text-emerald-700">{msg}</p>}
          <div className="mt-5 border-t border-slate-100 pt-4">
            <div className="font-medium text-navy-900">Mes droits</div>
            <div className="mt-3 flex flex-wrap gap-2"><Button variant="ghost" onClick={exporter}><Download size={16} /> Exporter toutes mes données</Button></div>
            <div className="mt-4 rounded-2xl bg-rose-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-rose-700"><Trash2 size={16} /> Supprimer mon compte et mes données</div>
              <p className="mt-1 text-xs text-rose-700">Analyses, réponses, messages, justificatifs et favoris sont effacés définitivement. Tapez SUPPRIMER pour confirmer.</p>
              <div className="mt-2 flex gap-2">
                <input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="SUPPRIMER" className="flex-1 rounded-xl border border-rose-200 px-3 py-2 text-sm" />
                <button onClick={supprimer} disabled={confirm !== 'SUPPRIMER'} className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Supprimer</button>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="overflow-x-auto">
        <SectionTitle sub="Chaque traitement, sa finalité, sa base légale, sa durée et ses destinataires.">
          <span className="flex items-center gap-2"><ScrollText size={18} className="text-gold-dark" /> Registre des traitements</span>
        </SectionTitle>
        <table className="w-full min-w-[800px] text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr>
            <th className="px-3 py-2">Traitement</th><th className="px-3 py-2">Finalité</th><th className="px-3 py-2">Données</th>
            <th className="px-3 py-2">Base légale</th><th className="px-3 py-2">Durée</th><th className="px-3 py-2">Destinataires</th></tr></thead>
          <tbody className="divide-y divide-slate-100 align-top">
            {registre.map((t) => (
              <tr key={t.traitement}><td className="px-3 py-2 font-medium text-navy-900">{t.traitement}</td><td className="px-3 py-2">{t.finalite}</td>
                <td className="px-3 py-2">{t.donnees}</td><td className="px-3 py-2">{t.base}</td><td className="px-3 py-2">{t.duree}</td><td className="px-3 py-2">{t.destinataires}</td></tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
