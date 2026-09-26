import clsx from 'clsx'
import { BookOpen, Bot, ExternalLink, FileText, FolderOpen, Landmark, Star, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { frDate } from '../api'
import { removeFavori, useFavoris, type FavoriType } from '../components/Favoris'
import { Card, ErrorBox, Spinner } from '../components/ui'

const TYPES: Record<FavoriType, { label: string; icon: typeof Star }> = {
  dossier: { label: 'Dossiers', icon: FolderOpen },
  dossier_admin: { label: 'Dossiers', icon: Landmark },
  article: { label: 'Articles de loi', icon: BookOpen },
  reponse: { label: 'Réponses', icon: FileText },
  assistant: { label: 'Réponses de l\'assistant', icon: Bot },
}

export default function FavorisPage() {
  const { items, ready, error } = useFavoris()
  const [filter, setFilter] = useState<FavoriType | ''>('')
  const [open, setOpen] = useState<string | null>(null)
  const navigate = useNavigate()
  const types = [...new Set(items.map((f) => f.type))]
  const shown = filter ? items.filter((f) => f.type === filter) : items

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-navy-900">Mes favoris</h1>
        <p className="mt-1 text-slate-500">Les dossiers, articles de loi et réponses que vous avez marqués d'une étoile.</p>
      </div>
      {error && <ErrorBox message={error} />}
      {!ready ? <Spinner label="Chargement des favoris…" /> : items.length === 0 ? (
        <Card className="py-12 text-center">
          <Star className="mx-auto text-gold" size={40} />
          <p className="mt-3 font-semibold text-navy-900">Aucun favori pour le moment</p>
          <p className="text-sm text-slate-500">Cliquez sur l'étoile d'un dossier, d'un article de loi ou d'une réponse pour le retrouver ici.</p>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setFilter('')} className={clsx('rounded-lg px-3 py-1.5 text-sm', !filter ? 'bg-navy-900 text-white' : 'bg-white ring-1 ring-slate-200')}>Tous · {items.length}</button>
            {types.map((t) => (
              <button key={t} onClick={() => setFilter(t)} className={clsx('rounded-lg px-3 py-1.5 text-sm', filter === t ? 'bg-navy-900 text-white' : 'bg-white ring-1 ring-slate-200')}>
                {TYPES[t].label} · {items.filter((f) => f.type === t).length}
              </button>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {shown.map((f) => {
              const Icon = TYPES[f.type].icon
              return (
                <Card key={f.id} className="flex flex-col">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gold-light text-gold-dark"><Icon size={20} /></div>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{TYPES[f.type].label} · {frDate(f.cree_le)}</div>
                      <div className="font-semibold text-navy-900">{f.titre}</div>
                    </div>
                    <button onClick={() => removeFavori(f.id)} aria-label="Retirer des favoris" className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600"><Trash2 size={16} /></button>
                  </div>
                  {f.extrait && (
                    <p className={clsx('mt-3 whitespace-pre-line text-sm text-slate-600', open !== f.id && 'line-clamp-3')}>{f.extrait}</p>
                  )}
                  <div className="mt-3 flex gap-3 text-sm">
                    {f.extrait.length > 180 && <button onClick={() => setOpen(open === f.id ? null : f.id)} className="font-medium text-navy-800">{open === f.id ? 'Réduire' : 'Tout lire'}</button>}
                    {f.lien && <button onClick={() => navigate(f.lien)} className="flex items-center gap-1 font-medium text-navy-800 hover:text-gold-dark">Ouvrir <ExternalLink size={14} /></button>}
                  </div>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
