import { Camera, RefreshCw, SwitchCamera, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button } from './ui'

/** Scan a paper notification with the webcam or the phone's rear camera; returns a JPEG file. */
export default function CameraScanner({ onCapture, onClose }: { onCapture: (f: File) => void; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const [facing, setFacing] = useState<'environment' | 'user'>('environment')
  const [shot, setShot] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setError('')
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1440 } }, audio: false })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return }
        stream.current = s
        if (video.current) { video.current.srcObject = s; void video.current.play() }
      })
      .catch(() => setError("Accès à la caméra refusé ou indisponible. Autorisez la caméra, ou déposez une photo à la place."))
    return () => { cancelled = true; stream.current?.getTracks().forEach((t) => t.stop()) }
  }, [facing])

  const capture = () => {
    const v = video.current
    if (!v || !v.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = v.videoWidth
    canvas.height = v.videoHeight
    const ctx = canvas.getContext('2d')!
    ctx.filter = 'contrast(1.15) brightness(1.05)'   // a little crisper for reading
    ctx.drawImage(v, 0, 0)
    setShot(canvas.toDataURL('image/jpeg', 0.92))
  }

  const confirm = async () => {
    if (!shot) return
    const blob = await (await fetch(shot)).blob()
    stream.current?.getTracks().forEach((t) => t.stop())
    onCapture(new File([blob], `scan_${Date.now()}.jpg`, { type: 'image/jpeg' }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/80 p-3 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Scanner une notification">
      <div className="relative w-full max-w-3xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <div className="font-semibold text-navy-900">Scanner la notification</div>
            <div className="text-xs text-slate-500">Posez la page à plat, bien éclairée, et cadrez-la entièrement.</div>
          </div>
          <button onClick={onClose} aria-label="Fermer" className="rounded-full p-1 text-slate-400 hover:bg-slate-100"><X size={20} /></button>
        </div>
        <div className="relative bg-navy-950">
          {error ? <p className="p-10 text-center text-sm text-rose-200">{error}</p> : shot ? (
            <img src={shot} alt="Page capturée" className="max-h-[60vh] w-full object-contain" />
          ) : (
            <>
              <video ref={video} playsInline muted className="max-h-[60vh] w-full object-contain" />
              <div className="pointer-events-none absolute inset-8 rounded-2xl border-2 border-dashed border-gold/80" />
            </>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-6 py-4">
          <Button variant="light" onClick={() => { setShot(null); setFacing(facing === 'environment' ? 'user' : 'environment') }}><SwitchCamera size={16} /> Changer de caméra</Button>
          {shot ? (
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setShot(null)}><RefreshCw size={16} /> Reprendre</Button>
              <Button variant="gold" onClick={confirm}>Analyser cette page</Button>
            </div>
          ) : <Button variant="gold" onClick={capture} disabled={!!error}><Camera size={16} /> Capturer</Button>}
        </div>
      </div>
    </div>
  )
}
