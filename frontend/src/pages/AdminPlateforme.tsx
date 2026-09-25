import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, articleLabel, type ArticleRef } from '../api'
import { Badge, Card, PageHeader, SectionTitle } from '../components/ui'

type Journal = Awaited<ReturnType<typeof api.journal>>

const ROLE_LABEL: Record<string, string> = {
  entreprise: 'Entreprise', conseil: 'Conseil fiscal', verificateur: 'Vérificateur',
  cheffe_contentieux: 'Cheffe du contentieux', admin: 'Administrateur',
}

export default function AdminPlateforme() {
  const [users, setUsers] = useState<Awaited<ReturnType<typeof api.utilisateurs>>>([])
  const [codes, setCodes] = useState<Awaited<ReturnType<typeof api.baseJuridique>>>([])
  const [journal, setJournal] = useState<Journal>([])
  const [q, setQ] = useState('délai de réponse notification')
  const [hits, setHits] = useState<ArticleRef[]>([])

  useEffect(() => {
    api.utilisateurs().then(setUsers).catch(() => {})
    api.baseJuridique().then(setCodes).catch(() => {})
    api.journal().then(setJournal).catch(() => {})
  }, [])
  const search = () => api.recherche(q).then(setHits).catch(() => setHits([]))

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Admin plateforme" title="Gouvernance de la plateforme"
        subtitle="Utilisateurs et rôles, base juridique et traçabilité de chaque recommandation de l'IA." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle sub="Chaque rôle ne voit que son espace (entreprise, administration, admin).">Utilisateurs et rôles</SectionTitle>
          <ul className="divide-y divide-slate-100 text-sm">
            {users.map((u) => (
              <li key={u.nom} className="flex items-center justify-between py-2.5">
                <div><div className="font-medium">{u.nom}</div><div className="text-xs text-slate-500">{u.structure}</div></div>
                <Badge tone={u.role === 'admin' ? 'rose' : u.role === 'entreprise' || u.role === 'conseil' ? 'sky' : 'emerald'}>{ROLE_LABEL[u.role] ?? u.role}</Badge>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <SectionTitle sub="Textes publics découpés article par article. À mettre à jour à chaque loi de finances.">Base juridique</SectionTitle>
          <ul className="space-y-2 text-sm">
            {codes.map((c) => (
              <li key={c.code} className="flex justify-between rounded-lg bg-slate-50 px-3 py-2"><span>{c.nom}</span><b>{c.articles} articles</b></li>
            ))}
          </ul>
          <div className="mt-4 flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()}
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Rechercher dans les textes" />
            <button onClick={search} className="flex items-center gap-1 rounded-lg bg-navy-900 px-3 py-2 text-sm text-white"><Search size={14} /> Chercher</button>
          </div>
          <ul className="mt-3 space-y-2">
            {hits.map((h) => (
              <li key={h.id} className="rounded-lg border border-slate-200 p-3 text-xs">
                <div className="font-semibold text-navy-900">{articleLabel(h.id)}</div>
                <div className="mt-1 text-slate-600">{h.extrait.slice(0, 280)}…</div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <Card className="overflow-x-auto">
        <SectionTitle sub="Chaque recommandation de l'IA est enregistrée : la décision finale reste humaine (loi organique 2004-63, traçabilité).">Journal des recommandations IA</SectionTitle>
        {journal.length === 0 ? <p className="text-sm text-slate-500">Aucune recommandation pour l'instant : analysez une notification ou ouvrez un dossier.</p> : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-500"><tr><th className="py-2">Horodatage</th><th>Action</th><th>Cible</th><th>Recommandation</th><th>Mode</th><th>Décision humaine</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {journal.map((j, i) => (
                <tr key={i}><td className="py-2 text-slate-500">{j.horodatage.replace('T', ' ')}</td><td>{j.action}</td><td>{j.cible}</td><td>{j.recommandation}</td>
                  <td><Badge tone={j.mode === 'ia' ? 'emerald' : 'slate'}>{j.mode}</Badge></td><td><Badge tone="amber">{j.decision_humaine}</Badge></td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
