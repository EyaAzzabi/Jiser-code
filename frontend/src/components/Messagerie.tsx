import clsx from 'clsx'
import { ArrowLeft, Check, CheckCheck, FileText, Lock, MessageSquarePlus, Paperclip, Send, Sparkles, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { wsUrl } from '../apiBase'
import { api, fileToBase64, loadSession, messagerieApi, type AideIA, type AnalyseResume, type Conversation, type Message } from '../api'
import { Button, Card, ErrorBox, PageHeader, Spinner } from './ui'

type Evenement = { type: string; conversation_id?: string; message?: Message; auteur_role?: string }

/** WebSocket to the messaging hub. The token is sent in the first message, never in the URL. */
export function useTempsReel(onEvent: (e: Evenement) => void) {
  const ws = useRef<WebSocket | null>(null)
  const handler = useRef(onEvent)
  handler.current = onEvent
  const [connecte, setConnecte] = useState(false)
  useEffect(() => {
    let stop = false
    let retry: ReturnType<typeof setTimeout>
    const connect = () => {
      const s = new WebSocket(wsUrl('/api/messagerie/ws'))
      ws.current = s
      s.onopen = () => s.send(JSON.stringify({ type: 'auth', token: loadSession()?.token }))
      s.onmessage = (m) => {
        const e = JSON.parse(m.data) as Evenement
        if (e.type === 'pret') setConnecte(true)
        handler.current(e)
      }
      s.onclose = () => { setConnecte(false); if (!stop) retry = setTimeout(connect, 3000) }
    }
    connect()
    return () => { stop = true; clearTimeout(retry); ws.current?.close() }
  }, [])
  const send = useCallback((e: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(e))
  }, [])
  return { send, connecte }
}

const heure = (iso: string) => new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

export default function Messagerie({ espace, base }: { espace: 'entreprise' | 'administration'; base: string }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const moi = loadSession()?.utilisateur?.id ?? ''
  const [liste, setListe] = useState<Conversation[] | null>(null)
  const [conv, setConv] = useState<Conversation | null>(null)
  const [analyses, setAnalyses] = useState<AnalyseResume[]>([])
  const [texte, setTexte] = useState('')
  const [piece, setPiece] = useState<File | null>(null)
  const [ecrit, setEcrit] = useState(false)
  const [aide, setAide] = useState<(AideIA & { action: string }) | null>(null)
  const [aideBusy, setAideBusy] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const bas = useRef<HTMLDivElement>(null)
  const dernierEcrit = useRef(0)

  const chargerListe = useCallback(() => messagerieApi.conversations().then(setListe).catch((e) => setError(e.message)), [])
  // opening a conversation marks it read: refresh the list so its unread badge disappears
  const chargerConv = useCallback((cid: string) => messagerieApi.conversation(cid).then((c) => { setConv(c); void chargerListe() })
    .catch((e) => setError(e.message)), [chargerListe])

  const { send, connecte } = useTempsReel((e) => {
    if (e.type === 'message' && e.message && e.conversation_id === id) {
      setConv((c) => (c && !c.messages?.some((m) => m.id === e.message!.id) ? { ...c, messages: [...(c.messages ?? []), e.message!] } : c))
      setEcrit(false)
      if (e.message.auteur_id !== moi && id) setTimeout(() => chargerConv(id), 400)   // marks it read and refreshes receipts
    }
    if (e.type === 'lu' && e.conversation_id === id && id) chargerConv(id)
    if (e.type === 'ecrit' && e.conversation_id === id) { setEcrit(true); setTimeout(() => setEcrit(false), 3000) }
    if (e.type === 'message' || e.type === 'activite') chargerListe()
  })

  useEffect(() => { chargerListe(); const t = setInterval(chargerListe, 30_000); return () => clearInterval(t) }, [chargerListe])
  useEffect(() => { if (espace === 'entreprise') api.analyses().then(setAnalyses).catch(() => {}) }, [espace])
  useEffect(() => {
    setAide(null); setConv(null)
    if (id) { chargerConv(id); send({ type: 'rejoindre', conversation_id: id }) }
  }, [id, chargerConv, send, connecte])
  useEffect(() => { const box = bas.current?.parentElement; if (box) box.scrollTo({ top: box.scrollHeight, behavior: 'smooth' }) }, [conv?.messages?.length, ecrit])

  const envoyer = async () => {
    if (!id || (!texte.trim() && !piece)) return
    setBusy(true); setError('')
    try {
      const p = piece ? { nom: piece.name, mime: piece.type || 'application/pdf', contenu: await fileToBase64(piece) } : undefined
      const m = await messagerieApi.envoyer(id, texte, p)
      setConv((c) => (c && !c.messages?.some((x) => x.id === m.id) ? { ...c, messages: [...(c.messages ?? []), m] } : c))
      setTexte(''); setPiece(null); chargerListe()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const demarrer = async (analyseId: string) => {
    try { const c = await messagerieApi.ouvrir(analyseId); await chargerListe(); navigate(`${base}/${c.id}`) } catch (e) { setError((e as Error).message) }
  }
  const demanderAide = async (action: 'resume' | 'suggestion' | 'pieces') => {
    if (!id) return
    setAideBusy(action)
    try { setAide({ ...(await messagerieApi.aide(id, action)), action }) } catch (e) { setError((e as Error).message) } finally { setAideBusy('') }
  }
  const ouvrirPiece = async (m: Message) => { try { window.open(await messagerieApi.pieceUrl(m.id), '_blank') } catch (e) { setError((e as Error).message) } }

  const sansConv = analyses.filter((a) => !liste?.some((c) => c.analyse_id === a.id || c.reference === a.reference))
  const titre = (c: Conversation) => (espace === 'entreprise' ? `CRCI ${c.gouvernorat}` : c.entreprise_nom)

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Échanges sécurisés" title="Messagerie"
        subtitle={espace === 'entreprise' ? "Échangez avec l'agent qui traite votre dossier, en temps réel. Pièces jointes et messages sont chiffrés."
          : "Les entreprises de votre centre vous écrivent ici. Seuls l'agent en charge et le chef de centre voient l'échange."}
        actions={<span className={clsx('flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium', connecte ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500')}>
          <span className={clsx('h-2 w-2 rounded-full', connecte ? 'animate-pulse bg-emerald-500' : 'bg-slate-400')} />{connecte ? 'Temps réel connecté' : 'Connexion…'}</span>} />
      {error && <ErrorBox message={error} />}
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <Card className={clsx('p-0', id && 'hidden lg:block')}>
          <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-navy-900">Conversations</div>
          {!liste ? <div className="p-4"><Spinner /></div> : (
            <ul className="max-h-[60vh] divide-y divide-slate-100 overflow-y-auto">
              {liste.length === 0 && <li className="p-4 text-sm text-slate-500">Aucune conversation pour le moment.</li>}
              {liste.map((c) => (
                <li key={c.id}>
                  <button onClick={() => navigate(`${base}/${c.id}`)} className={clsx('w-full px-4 py-3 text-left hover:bg-canvas', c.id === id && 'bg-bridge-light')}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-semibold text-navy-900">{titre(c)}</span>
                      {!!c.non_lus && <span className="rounded-full bg-gold px-2 text-xs font-bold text-white">{c.non_lus}</span>}
                    </div>
                    <div className="text-xs text-slate-500">{c.reference}{c.agent ? ` · ${c.agent}` : ''}</div>
                    {c.dernier && <div className="mt-1 truncate text-sm text-slate-600">{c.dernier.extrait || '📎 Pièce jointe'}</div>}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {espace === 'entreprise' && sansConv.length > 0 && (
            <div className="border-t border-slate-100 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Démarrer un échange</div>
              {sansConv.map((a) => (
                <button key={a.id} onClick={() => demarrer(a.id)} className="mt-2 flex w-full items-center gap-2 rounded-xl bg-canvas px-3 py-2 text-left text-sm hover:bg-gold-light/60">
                  <MessageSquarePlus size={16} className="text-gold-dark" /><span className="truncate">{a.reference}</span>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card className={clsx('flex min-h-[60vh] flex-col p-0', !id && 'hidden lg:flex')}>
          {!id ? (
            <div className="m-auto max-w-sm p-8 text-center text-slate-500"><Lock className="mx-auto mb-2 text-gold" />Choisissez une conversation.</div>
          ) : !conv ? <div className="p-6"><Spinner /></div> : (
            <>
              <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-4 py-3">
                <button onClick={() => navigate(base)} className="rounded-lg p-1 hover:bg-slate-100 lg:hidden" aria-label="Retour"><ArrowLeft size={18} /></button>
                <div className="min-w-0 basis-full">
                  <div className="font-semibold text-navy-900">{titre(conv)} · {conv.reference}</div>
                  <div className="flex items-center gap-1 text-xs text-slate-500"><Lock size={12} className="text-gold" /> Messages chiffrés · visibles uniquement par l'entreprise, l'agent en charge{conv.agent ? ` (${conv.agent})` : ''} et le chef de centre</div>
                </div>
                <div className="flex basis-full flex-wrap gap-2">
                  {([['resume', 'Résumer'], ['suggestion', 'Suggérer une réponse'], ['pieces', 'Pièces manquantes']] as const).map(([a, l]) => (
                    <button key={a} onClick={() => demanderAide(a)} disabled={!!aideBusy}
                      className="flex items-center gap-1 rounded-full bg-gold-light px-3 py-1 text-xs font-semibold text-gold-dark ring-1 ring-gold/30 hover:bg-gold hover:text-white disabled:opacity-50">
                      <Sparkles size={12} />{aideBusy === a ? '…' : l}
                    </button>
                  ))}
                </div>
              </div>
              {aide && (
                <div className="mx-4 mt-3 rounded-2xl border border-gold/30 bg-gold-light/40 p-3 text-sm">
                  <div className="flex items-start gap-2">
                    <Sparkles size={16} className="mt-0.5 shrink-0 text-gold-dark" />
                    <div className="flex-1">
                      <p className="whitespace-pre-line text-slate-700">{aide.texte}</p>
                      {aide.points.length > 0 && <ul className="mt-1 list-disc pl-5 text-slate-700">{aide.points.map((p) => <li key={p}>{p}</li>)}</ul>}
                      {aide.action === 'suggestion' && <button onClick={() => setTexte(aide.texte)} className="mt-2 text-xs font-semibold text-navy-900 underline decoration-gold underline-offset-4">Utiliser ce texte</button>}
                      <div className="mt-1 text-[11px] text-slate-500">Suggestion de l'IA (texte pseudonymisé), à relire avant envoi.</div>
                    </div>
                    <button onClick={() => setAide(null)} aria-label="Fermer"><X size={14} /></button>
                  </div>
                </div>
              )}
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {(conv.messages ?? []).length === 0 && <p className="text-center text-sm text-slate-400">Aucun message. Écrivez le premier.</p>}
                {(conv.messages ?? []).map((m) => {
                  const mine = m.auteur_id === moi
                  const lu = m.lu_par.some((x) => x !== m.auteur_id)
                  return (
                    <div key={m.id} className={clsx('flex', mine ? 'justify-end' : 'justify-start')}>
                      <div className={clsx('max-w-[78%] rounded-2xl px-4 py-2.5 text-sm shadow-sm', mine ? 'rounded-br-md bg-navy-900 text-white' : 'rounded-bl-md bg-canvas text-slate-800')}>
                        {!mine && <div className="mb-0.5 text-xs font-semibold text-gold-dark">{m.auteur_nom}</div>}
                        {m.contenu && <p className="whitespace-pre-line" dir="auto">{m.contenu}</p>}
                        {m.a_piece && (
                          <button onClick={() => ouvrirPiece(m)} className={clsx('mt-1 flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs', mine ? 'bg-white/10' : 'bg-white ring-1 ring-slate-200')}>
                            <FileText size={14} />{m.piece_nom}
                          </button>
                        )}
                        <div className={clsx('mt-1 flex items-center justify-end gap-1 text-[10px]', mine ? 'text-slate-300' : 'text-slate-400')}>
                          {heure(m.cree_le)}{mine && (lu ? <CheckCheck size={12} className="text-gold" /> : <Check size={12} />)}
                        </div>
                      </div>
                    </div>
                  )
                })}
                {ecrit && <div className="text-xs italic text-slate-400">{espace === 'entreprise' ? "L'agent écrit…" : "L'entreprise écrit…"}</div>}
                <div ref={bas} />
              </div>
              <div className="border-t border-slate-100 p-3">
                {piece && <div className="mb-2 flex items-center gap-2 text-xs text-slate-600"><Paperclip size={14} />{piece.name}<button onClick={() => setPiece(null)}><X size={12} /></button></div>}
                <div className="flex items-end gap-2">
                  <label className="cursor-pointer rounded-xl p-2.5 text-slate-500 hover:bg-slate-100" title="Joindre une pièce (PDF ou image, 5 Mo)">
                    <Paperclip size={18} />
                    <input type="file" className="hidden" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setPiece(e.target.files?.[0] ?? null)} />
                  </label>
                  <textarea value={texte} rows={2} placeholder="Écrivez votre message…" className="flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-gold focus:ring-2 focus:ring-gold/30"
                    onChange={(e) => {
                      setTexte(e.target.value)
                      if (Date.now() - dernierEcrit.current > 2000) { dernierEcrit.current = Date.now(); send({ type: 'ecrit', conversation_id: id }) }
                    }}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void envoyer() } }} />
                  <Button onClick={envoyer} disabled={busy || (!texte.trim() && !piece)}><Send size={16} /></Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
