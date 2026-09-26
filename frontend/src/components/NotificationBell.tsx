import clsx from 'clsx'
import { AlarmClock, Bell } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loadSession } from '../api'

interface Item {
  id: string
  niveau: 'urgent' | 'bientot' | 'info'
  titre: string
  detail: string
  lien: string
  jours: number
}

const DOT = { urgent: 'bg-rose-500', bientot: 'bg-amber-500', info: 'bg-bridge' }

/** In-app bell: upcoming deadlines, refreshed every few minutes. */
export default function NotificationBell() {
  const [data, setData] = useState<{ total: number; urgents: number; items: Item[] } | null>(null)
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const load = () => {
      const token = loadSession()?.token
      fetch('/api/notifications', { headers: token ? { Authorization: `Bearer ${token}` } : {} })
        .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {})
    }
    load()
    const t = setInterval(load, 5 * 60 * 1000)
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => { clearInterval(t); document.removeEventListener('mousedown', close) }
  }, [])

  const total = data?.total ?? 0
  return (
    <div ref={box} className="relative">
      <button onClick={() => setOpen(!open)} aria-label={`Notifications : ${total}`}
        className="relative flex h-11 w-11 items-center justify-center rounded-full bg-white text-navy-900 shadow-sm ring-1 ring-slate-200 hover:ring-gold">
        <Bell size={20} />
        {total > 0 && (
          <span className={clsx('absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-bold text-white',
            data?.urgents ? 'animate-pulse bg-rose-500' : 'bg-gold')}>{total}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-96 overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-slate-200">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <span className="font-semibold text-navy-900">Rappels et échéances</span>
            <span className="text-xs text-slate-500">{total} en cours</span>
          </div>
          {total === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-slate-500">Aucune échéance dans les 15 prochains jours.</p>
          ) : (
            <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
              {data!.items.map((i) => (
                <li key={i.id}>
                  <button onClick={() => { setOpen(false); navigate(i.lien) }} className="flex w-full gap-3 px-4 py-3 text-left hover:bg-canvas">
                    <span className={clsx('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', DOT[i.niveau])} />
                    <span>
                      <span className="flex items-center gap-1 text-sm font-semibold text-navy-900"><AlarmClock size={14} /> {i.titre}</span>
                      <span className="block text-xs text-slate-500">{i.detail}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="border-t border-slate-100 px-4 py-2 text-[11px] text-slate-400">Vous recevez aussi ces rappels par e-mail (J-15, J-7, J-3, J-1).</p>
        </div>
      )}
    </div>
  )
}
