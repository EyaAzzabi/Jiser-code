import clsx from 'clsx'
import { BookOpen, CheckCircle2, Database, Mail, ScrollText, Search, Server, Sparkles, Users, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { api, articleLabel, frDate, type ArticleRef, type Session } from '../api'
import AppShell, { type NavItem } from '../components/AppShell'
import { LoginForm } from '../components/Login'
import { Badge, Card, SectionTitle, Spinner } from '../components/ui'

const NAV: NavItem[] = [
  { to: '/plateforme', label: 'Vue d\'ensemble', icon: Server, end: true },
  { to: '/plateforme/utilisateurs', label: 'Utilisateurs', icon: Users },
  { to: '/plateforme/journal', label: 'Journal IA', icon: ScrollText },
  { to: '/plateforme/base-juridique', label: 'Base juridique', icon: BookOpen },
]

const ROLE_LABEL: Record<string, string> = {
  entreprise: 'Entreprise', conseil: 'Conseil fiscal', verificateur: 'Vérificateur', contentieux: 'Contentieux', admin: 'Administrateur',
}

function Title({ title, sub }: { title: string; sub: string }) {
  return <div><h1 className="text-3xl font-bold text-navy-900">{title}</h1><p className="mt-1 text-slate-500">{sub}</p></div>
}

function Overview() {
  const [s, setS] = useState<Awaited<ReturnType<typeof api.systeme>> | null>(null)
  const [users, setUsers] = useState<number | null>(null)
  useEffect(() => {
    api.systeme().then(setS).catch(() => {})
    api.utilisateurs().then((u) => setUsers(u.length)).catch(() => {})
  }, [])
  if (!s) return <Spinner />
  const items = [
    { icon: Sparkles, label: 'IA générative', ok: s.llm.ia, detail: s.llm.ia ? `${s.llm.fournisseur ?? ''} · ${s.llm.modele ?? ''}` : s.llm.raison },
    { icon: Database, label: 'Base de données', ok: s.base === 'supabase', detail: s.base === 'supabase' ? 'Supabase (PostgreSQL)' : 'Mémoire locale (Supabase non configuré)' },
    { icon: Mail, label: 'E-mail OTP (n8n)', ok: s.n8n_otp, detail: s.n8n_otp ? 'Webhook configuré' : 'Non configuré : codes dans le journal serveur' },
    { icon: Mail, label: 'E-mail de bienvenue (n8n)', ok: s.n8n_bienvenue, detail: s.n8n_bienvenue ? 'Webhook configuré' : 'Non configuré' },
  ]
  return (
    <div className="space-y-6">
      <Title title="Vue d'ensemble" sub="État des services de la plateforme." />
      <div className="grid gap-4 md:grid-cols-2">
        {items.map(({ icon: Icon, label, ok, detail }) => (
          <Card key={label} className="flex items-center gap-4">
            <div className={clsx('flex h-11 w-11 items-center justify-center rounded-2xl', ok ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600')}><Icon size={22} /></div>
            <div className="flex-1"><div className="font-semibold text-navy-900">{label}</div><div className="text-sm text-slate-500">{detail}</div></div>
            {ok ? <CheckCircle2 className="text-emerald-500" /> : <XCircle className="text-amber-500" />}
          </Card>
        ))}
      </div>
      <Card><SectionTitle>Comptes créés</SectionTitle><div className="font-display text-3xl font-bold text-navy-900">{users ?? '—'}</div></Card>
    </div>
  )
}

function Utilisateurs() {
  const [users, setUsers] = useState<Awaited<ReturnType<typeof api.utilisateurs>> | null>(null)
  useEffect(() => { api.utilisateurs().then(setUsers).catch(() => setUsers([])) }, [])
  return (
    <div className="space-y-6">
      <Title title="Utilisateurs" sub="Comptes créés par l'onboarding sécurisé (e-mail vérifié par code à usage unique)." />
      <Card className="overflow-x-auto p-0">
        {!users ? <div className="p-5"><Spinner /></div> : users.length === 0 ? <p className="p-5 text-sm text-slate-500">Aucun compte pour le moment.</p> : (
          <table className="w-full text-sm">
            <thead className="whitespace-nowrap bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr><th className="px-5 py-2">Nom</th><th className="px-5 py-2">E-mail</th><th className="px-5 py-2">Rôle</th><th className="px-5 py-2">Structure</th><th className="px-5 py-2">Inscription</th><th className="px-5 py-2">Dernière connexion</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-5 py-3 font-medium text-navy-900">{u.prenom} {u.nom}</td>
                  <td className="px-5 py-3 text-slate-600">{u.email}</td>
                  <td className="px-5 py-3"><Badge tone={u.role === 'entreprise' || u.role === 'conseil' ? 'sky' : 'emerald'}>{ROLE_LABEL[u.role] ?? u.role}</Badge></td>
                  <td className="px-5 py-3 text-slate-600">{String(u.details?.raison_sociale ?? u.details?.cabinet ?? u.details?.structure ?? '—')}</td>
                  <td className="px-5 py-3 text-slate-500">{frDate(u.cree_le)}</td>
                  <td className="px-5 py-3 text-slate-500">{u.derniere_connexion ? frDate(u.derniere_connexion) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

function Journal() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof api.journal>> | null>(null)
  useEffect(() => { api.journal().then(setRows).catch(() => setRows([])) }, [])
  return (
    <div className="space-y-6">
      <Title title="Journal des recommandations IA" sub="Chaque recommandation et chaque décision humaine est tracée (loi organique 2004-63)." />
      <Card className="overflow-x-auto p-0">
        {!rows ? <div className="p-5"><Spinner /></div> : (
          <table className="w-full text-sm">
            <thead className="whitespace-nowrap bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr><th className="px-5 py-2">Horodatage</th><th className="px-5 py-2">Action</th><th className="px-5 py-2">Cible</th><th className="px-5 py-2">Recommandation</th><th className="px-5 py-2">Moteur</th><th className="px-5 py-2">Décision humaine</th><th className="px-5 py-2">Utilisateur</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((j, i) => (
                <tr key={i}>
                  <td className="whitespace-nowrap px-5 py-2.5 text-slate-500">{new Date(j.horodatage).toLocaleString('fr-FR')}</td>
                  <td className="px-5 py-2.5">{j.action}</td><td className="px-5 py-2.5">{j.cible}</td><td className="px-5 py-2.5">{j.recommandation}</td>
                  <td className="px-5 py-2.5"><Badge tone={j.mode === 'ia' ? 'gold' : j.mode === 'humain' ? 'emerald' : 'slate'}>{j.mode}</Badge></td>
                  <td className="px-5 py-2.5"><Badge tone={j.decision_humaine === 'en attente' ? 'amber' : 'emerald'}>{j.decision_humaine}</Badge></td>
                  <td className="px-5 py-2.5 text-slate-500">{j.utilisateur ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

function BaseJuridique() {
  const [codes, setCodes] = useState<Awaited<ReturnType<typeof api.baseJuridique>>>([])
  const [q, setQ] = useState('délai de réponse notification')
  const [hits, setHits] = useState<ArticleRef[]>([])
  useEffect(() => { api.baseJuridique().then(setCodes).catch(() => {}) }, [])
  const search = () => api.recherche(q).then(setHits).catch(() => setHits([]))
  return (
    <div className="space-y-6">
      <Title title="Base juridique" sub="Textes découpés article par article, indexés pour la recherche. À mettre à jour à chaque loi de finances." />
      <div className="grid gap-4 md:grid-cols-3">
        {codes.map((c) => <Card key={c.code}><div className="text-sm text-slate-500">{c.nom}</div><div className="mt-1 font-display text-2xl font-bold text-navy-900">{c.articles} articles</div><div className="text-xs text-slate-400">{c.source}</div></Card>)}
      </div>
      <Card>
        <div className="flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} className="flex-1 rounded-xl border border-slate-300 px-3 py-2.5 text-sm" placeholder="Rechercher dans les textes" />
          <button onClick={search} className="flex items-center gap-1 rounded-xl bg-navy-900 px-4 text-sm text-white"><Search size={14} /> Chercher</button>
        </div>
        <ul className="mt-4 space-y-2">
          {hits.map((h) => <li key={h.id} className="rounded-xl border border-slate-200 p-3 text-sm"><div className="font-semibold text-navy-900">{articleLabel(h.id)}</div><div className="mt-1 text-slate-600">{h.extrait}</div></li>)}
        </ul>
      </Card>
    </div>
  )
}

export default function AdminPlateforme({ session }: { session: Session | null }) {
  if (session?.role !== 'admin') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-navy-950 to-navy-800 p-4">
        <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl">
          <LoginForm intention="admin" onDone={() => { /* the session change re-renders this page */ }} />
        </div>
      </div>
    )
  }
  return (
    <AppShell session={session} espace="Administration plateforme" nav={NAV}>
      <Routes>
        <Route index element={<Overview />} />
        <Route path="utilisateurs" element={<Utilisateurs />} />
        <Route path="journal" element={<Journal />} />
        <Route path="base-juridique" element={<BaseJuridique />} />
      </Routes>
    </AppShell>
  )
}
