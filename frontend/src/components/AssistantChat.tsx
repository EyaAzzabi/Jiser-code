import clsx from 'clsx'
import { Send, Sparkles, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { articleLabel, loadSession, type ArticleRef } from '../api'
import { StarButton } from './Favoris'
import ListenButton from './ListenButton'

interface Message {
  role: 'utilisateur' | 'assistant'
  texte: string
  articles?: ArticleRef[]
  mode?: string
  streaming?: boolean
}

const WELCOME = {
  fr: 'Bonjour ! Je suis l\'assistant fiscal de JISER. Posez-moi une question sur votre notification, les délais, la procédure ou vos droits.',
  derja: 'Ahla ! Ana l\'assistant fiscal mte3 JISER. Es2alni 3la notification mte3ek, el délais, el procédure walla 7a9ou9ek.',
}
const STARTERS = {
  fr: ['Quel est mon délai pour répondre ?', "Qu'est-ce que la taxation d'office ?", 'Comment contester un redressement de TVA ?'],
  derja: ['9addeh 3andi wa9t bech njeweb ?', 'Chnowa ma3neha taxation d\'office ?', 'Kifech nconteste redressement mte3 TVA ?'],
}

export default function AssistantChat({ langue, analyseId, compact }: { langue: 'fr' | 'derja'; analyseId?: string; compact?: boolean }) {
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', texte: WELCOME[langue] }])
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS[langue])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setMessages([{ role: 'assistant', texte: WELCOME[langue] }])
    setSuggestions(STARTERS[langue])
  }, [langue])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [messages])

  const ask = async (q: string) => {
    if (!q.trim() || busy) return
    const history = messages.filter((m) => m.texte !== WELCOME[langue]).map((m) => ({ role: m.role, texte: m.texte }))
    setMessages((m) => [...m, { role: 'utilisateur', texte: q }])
    setInput(''); setBusy(true)
    // streamed answer: NDJSON events (articles, then text deltas, then suggestions)
    const update = (patch: (last: Message) => Message) =>
      setMessages((m) => [...m.slice(0, -1), patch(m[m.length - 1])])
    setMessages((m) => [...m, { role: 'assistant', texte: '', streaming: true }])
    try {
      const token = loadSession()?.token
      const res = await fetch('/api/contribuable/assistant/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ question: q, langue, historique: history, analyse_id: analyseId }),
      })
      if (!res.ok || !res.body) throw new Error(`${res.status}`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.trim()) continue
          const ev = JSON.parse(line)
          if (ev.type === 'articles') update((l) => ({ ...l, articles: ev.articles }))
          else if (ev.type === 'delta') update((l) => ({ ...l, texte: l.texte + ev.text }))
          else if (ev.type === 'fin') {
            update((l) => ({ ...l, mode: ev.mode, streaming: false }))
            if (ev.suggestions?.length) setSuggestions(ev.suggestions)
          }
        }
      }
      update((l) => ({ ...l, streaming: false }))
    } catch (e) {
      update((l) => ({ ...l, texte: l.texte || `Erreur : ${(e as Error).message}`, streaming: false }))
    } finally { setBusy(false) }
  }

  return (
    <div className={clsx('flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm', compact ? 'h-[520px]' : 'h-[640px]')}>
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.map((m, i) => (
          <div key={i} className={clsx('flex gap-3', m.role === 'utilisateur' && 'flex-row-reverse')}>
            <div className={clsx('flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
              m.role === 'assistant' ? 'bg-gradient-to-br from-gold to-gold-dark text-white' : 'bg-navy-900 text-white')}>
              {m.role === 'assistant' ? <Sparkles size={15} /> : <User size={15} />}
            </div>
            <div className={clsx('max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
              m.role === 'assistant' ? 'bg-canvas text-slate-700' : 'bg-navy-900 text-white')}>
              <p className="whitespace-pre-line">{m.texte}{m.streaming && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-gold align-middle" />}</p>
              {m.articles && m.articles.length > 0 && (
                <div className="mt-3 space-y-1.5 border-t border-slate-200 pt-2">
                  {m.articles.map((a) => (
                    <details key={a.id} className="text-xs">
                      <summary className="cursor-pointer font-semibold text-navy-800">{articleLabel(a.id)}</summary>
                      <p className="mt-1 text-slate-500">{a.extrait}</p>
                    </details>
                  ))}
                </div>
              )}
              {m.mode === 'hors_ligne' && <p className="mt-2 text-[11px] text-slate-400">Réponse sans IA générative (recherche dans les textes).</p>}
              {m.role === 'assistant' && m.mode === 'ia' && !m.streaming && (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ListenButton text={m.texte} source={langue} />
                  <StarButton type="assistant" refId={`${m.texte.length}-${m.texte.slice(0, 60)}`}
                    titre={messages[i - 1]?.texte ? `Question : ${messages[i - 1].texte.slice(0, 120)}` : 'Réponse de l\'assistant'} extrait={m.texte} />
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && !messages[messages.length - 1]?.streaming && <div className="flex gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-gold text-white"><Sparkles size={15} /></div>
          <div className="flex items-center gap-1 rounded-2xl bg-canvas px-4 py-3">{[0, 1, 2].map((i) => <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-gold" style={{ animationDelay: `${i * 120}ms` }} />)}</div></div>}
        <div ref={end} />
      </div>
      <div className="border-t border-slate-100 p-3">
        <div className="mb-2 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button key={s} onClick={() => ask(s)} disabled={busy} className="rounded-full bg-gold-light/70 px-3 py-1 text-xs text-navy-900 ring-1 ring-gold/30 hover:bg-gold hover:text-white">{s}</button>
          ))}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); void ask(input) }} className="flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={langue === 'derja' ? 'Ekteb so2alek…' : 'Écrivez votre question…'}
            className="flex-1 rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-gold focus:ring-2 focus:ring-gold/30" />
          <button type="submit" disabled={busy || !input.trim()} aria-label="Envoyer" className="rounded-xl bg-navy-900 px-4 text-white hover:bg-navy-800 disabled:opacity-40"><Send size={16} /></button>
        </form>
      </div>
    </div>
  )
}
