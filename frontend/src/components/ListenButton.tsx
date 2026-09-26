import clsx from 'clsx'
import { Loader2, Square, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { loadSession } from '../api'

type Lang = 'fr' | 'en' | 'derja'
const LABELS: Record<Lang, string> = { fr: 'FR', en: 'EN', derja: 'Tounsi' }

// audio already synthesised in this tab, keyed by language + text
const cache = new Map<string, string>()
let playing: HTMLAudioElement | null = null

/** Reads a text aloud in French, English or Tunisian derja (OpenAI TTS through the API). */
export default function ListenButton({ text, source = 'fr', tone = 'light', defaultLang }: {
  text: string
  source?: 'fr' | 'derja'
  tone?: 'light' | 'dark'
  defaultLang?: Lang
}) {
  const [lang, setLang] = useState<Lang>(defaultLang ?? (source === 'derja' ? 'derja' : 'fr'))
  const [state, setState] = useState<'idle' | 'loading' | 'playing' | 'error'>('idle')
  const audio = useRef<HTMLAudioElement | null>(null)
  useEffect(() => () => { audio.current?.pause() }, [])

  const stop = () => { audio.current?.pause(); setState('idle') }

  const play = async (l: Lang = lang) => {
    playing?.pause()   // one voice at a time on the page
    setState('loading')
    try {
      const key = `${l}|${source}|${text}`
      let url = cache.get(key)
      if (!url) {
        const token = loadSession()?.token
        const res = await fetch('/api/voix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify({ texte: text, source, langue: l }),
        })
        if (!res.ok) throw new Error(String(res.status))
        url = URL.createObjectURL(await res.blob())
        cache.set(key, url)
      }
      const a = new Audio(url)
      audio.current = a
      playing = a
      a.onended = () => setState('idle')
      await a.play()
      setState('playing')
    } catch {
      setState('error')
    }
  }

  const dark = tone === 'dark'
  return (
    <div className={clsx('inline-flex items-center gap-1 rounded-full p-1 text-xs', dark ? 'bg-white/10' : 'bg-gold-light/70 ring-1 ring-gold/30')}>
      <button onClick={() => (state === 'playing' ? stop() : play())} disabled={state === 'loading'}
        aria-label={state === 'playing' ? 'Arrêter la lecture' : 'Écouter l\'explication'}
        className={clsx('flex items-center gap-1.5 rounded-full px-2.5 py-1 font-semibold', dark ? 'bg-gold text-white hover:bg-gold-dark' : 'bg-navy-900 text-white hover:bg-navy-800')}>
        {state === 'loading' ? <Loader2 size={13} className="animate-spin" /> : state === 'playing' ? <Square size={12} /> : <Volume2 size={13} />}
        {state === 'playing' ? 'Stop' : state === 'error' ? 'Réessayer' : 'Écouter'}
      </button>
      {(Object.keys(LABELS) as Lang[]).map((l) => (
        <button key={l} onClick={() => { setLang(l); if (state === 'playing' || state === 'idle') void play(l) }}
          className={clsx('rounded-full px-2 py-1 font-medium', lang === l
            ? (dark ? 'bg-white text-navy-900' : 'bg-white text-navy-900 shadow-sm')
            : (dark ? 'text-slate-200 hover:bg-white/10' : 'text-slate-600 hover:bg-white/70'))}>
          {LABELS[l]}
        </button>
      ))}
    </div>
  )
}
