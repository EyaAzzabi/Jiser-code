import clsx from 'clsx'
import { Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { loadSession } from '../api'

export type FavoriType = 'dossier' | 'article' | 'reponse' | 'assistant' | 'dossier_admin'

export interface Favori {
  id: string
  type: FavoriType
  ref: string
  titre: string
  extrait: string
  lien: string
  cree_le: string
}

// One shared list for the whole page, so every star stays in sync.
let items: Favori[] | null = null
let loading: Promise<void> | null = null
let error = ''
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((fn) => fn())

async function call(path: string, init: RequestInit = {}) {
  const token = loadSession()?.token
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* keep status text */ }
    throw new Error(detail)
  }
  return res.json()
}

export function reloadFavoris() {
  loading = call('/api/favoris')
    .then((r: Favori[]) => { items = r; error = '' })
    .catch((e: Error) => { items = []; error = e.message })
    .finally(() => { loading = null; emit() })
  return loading
}

export function useFavoris() {
  const [, force] = useState(0)
  useEffect(() => {
    const fn = () => force((n) => n + 1)
    listeners.add(fn)
    if (items === null && !loading) void reloadFavoris()
    return () => { listeners.delete(fn) }
  }, [])
  return { items: items ?? [], ready: items !== null, error }
}

export async function toggleFavori(f: Omit<Favori, 'id' | 'cree_le'>) {
  const existing = items?.find((x) => x.type === f.type && x.ref === f.ref)
  if (existing) {
    items = items!.filter((x) => x.id !== existing.id)
    emit()
    await call(`/api/favoris/${existing.id}`, { method: 'DELETE' }).catch(() => reloadFavoris())
  } else {
    const saved: Favori = await call('/api/favoris', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f),
    })
    items = [saved, ...(items ?? [])]
    emit()
  }
}

export async function removeFavori(id: string) {
  items = (items ?? []).filter((x) => x.id !== id)
  emit()
  await call(`/api/favoris/${id}`, { method: 'DELETE' }).catch(() => reloadFavoris())
}

/** Star toggle to pin any item (analysis, law article, reply, assistant answer, admin file). */
export function StarButton({ type, refId, titre, extrait = '', lien = '', tone = 'light', label }: {
  type: FavoriType
  refId: string
  titre: string
  extrait?: string
  lien?: string
  tone?: 'light' | 'dark'
  label?: boolean
}) {
  const { items: favs } = useFavoris()
  const [busy, setBusy] = useState(false)
  const on = favs.some((x) => x.type === type && x.ref === refId)
  const click = async () => {
    setBusy(true)
    try { await toggleFavori({ type, ref: refId, titre, extrait: extrait.slice(0, 1000), lien }) } catch { /* the list reloads itself */ }
    finally { setBusy(false) }
  }
  return (
    <button onClick={click} disabled={busy} aria-pressed={on} title={on ? 'Retirer des favoris' : 'Ajouter aux favoris'}
      className={clsx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold transition',
        tone === 'dark' ? (on ? 'bg-gold text-white' : 'bg-white/10 text-white hover:bg-white/20')
          : (on ? 'bg-gold text-white' : 'bg-white text-navy-900 ring-1 ring-slate-300 hover:ring-gold'))}>
      <Star size={14} className={clsx(on && 'fill-current')} />
      {label && (on ? 'Dans mes favoris' : 'Ajouter aux favoris')}
    </button>
  )
}
