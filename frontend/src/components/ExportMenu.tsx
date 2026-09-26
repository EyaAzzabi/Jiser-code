import clsx from 'clsx'
import { Download, Loader2, Mail, Share2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { loadSession } from '../api'

/** Share / export a PDF: download it, share it (system share sheet with the file) or prepare an e-mail. */
export default function ExportMenu({ url, filename, subject, body, tone = 'light' }: {
  url: string
  filename: string
  subject: string
  body: string
  tone?: 'light' | 'dark'
}) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const getPdf = async (): Promise<File> => {
    const token = loadSession()?.token
    const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!res.ok) throw new Error('Export impossible')
    return new File([await res.blob()], filename, { type: 'application/pdf' })
  }
  const download = (file: File) => {
    const href = URL.createObjectURL(file)
    const a = document.createElement('a'); a.href = href; a.download = filename; a.click()
    setTimeout(() => URL.revokeObjectURL(href), 2000)
  }

  const run = async (action: 'download' | 'share' | 'mail') => {
    setBusy(true); setNote('')
    try {
      const file = await getPdf()
      if (action === 'download') {
        download(file)
      } else if (action === 'share') {
        if (navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], title: subject, text: body })
        } else {
          download(file)
          setNote('Partage direct non disponible sur ce navigateur : le PDF a été téléchargé.')
        }
      } else {
        download(file)
        window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(`${body}\n\n(Le PDF « ${filename} » vient d'être téléchargé : joignez-le à ce message.)`)}`
      }
      setOpen(false)
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setNote((e as Error).message)
    } finally { setBusy(false) }
  }

  const dark = tone === 'dark'
  return (
    <div ref={box} className="relative">
      <button onClick={() => setOpen(!open)} disabled={busy}
        className={clsx('inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold',
          dark ? 'bg-white/10 text-white hover:bg-white/20' : 'bg-white text-navy-900 ring-1 ring-slate-300 hover:ring-gold')}>
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />} Partager / exporter
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-64 overflow-hidden rounded-2xl bg-white py-1 text-sm text-navy-900 shadow-xl ring-1 ring-slate-200">
          <button onClick={() => run('download')} className="flex w-full items-center gap-2 px-4 py-2.5 hover:bg-canvas"><Download size={16} /> Télécharger le PDF</button>
          <button onClick={() => run('share')} className="flex w-full items-center gap-2 px-4 py-2.5 hover:bg-canvas"><Share2 size={16} /> Partager le PDF…</button>
          <button onClick={() => run('mail')} className="flex w-full items-center gap-2 px-4 py-2.5 hover:bg-canvas"><Mail size={16} /> Envoyer par e-mail</button>
        </div>
      )}
      {note && <p className={clsx('absolute right-0 mt-2 w-72 rounded-xl p-2 text-xs shadow', dark ? 'bg-white text-slate-700' : 'bg-gold-light text-navy-900')}>{note}</p>}
    </div>
  )
}
