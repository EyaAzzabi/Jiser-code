import clsx from 'clsx'
import { Activity, BellRing, BookOpen, BrainCircuit, Handshake, CheckCircle2, Database, Mail, ScrollText, Search, Server, Sparkles, Users, XCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Route, Routes } from 'react-router-dom'
import { api, articleLabel, frDate, type ArticleRef, type Session } from '../api'
import AppShell, { type NavItem } from '../components/AppShell'
import { LoginForm } from '../components/Login'
import { Badge, Button, Card, SectionTitle, Spinner } from '../components/ui'

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

const ACTION_LABEL: Record<string, string> = {
  analyse_notification: 'Analyses de notification', brouillon_reponse: 'Brouillons de réponse', assistant: "Questions à l'assistant",
  avis_ia: 'Avis IA sur dossier', decision_conciliation: 'Décisions de conciliation', amelioration_motivation: 'Motivations renforcées',
  controle_qualite: 'Contrôles qualité', synthese_stock: 'Synthèses du stock', rappel_email: 'Rappels e-mail envoyés', otp_verifie: 'Connexions vérifiées (OTP)', inscription: 'Inscriptions',
}
const PIE = ['#0b2f5b', '#c29a2e', '#2f74c0', '#10b981', '#e11d48']

type JournalRow = Awaited<ReturnType<typeof api.journal>>[number]
type UserRow = Awaited<ReturnType<typeof api.utilisateurs>>[number]

/** Live pulse of the platform, computed from the audit trail and the accounts. */
function Pulse({ journal, users }: { journal: JournalRow[]; users: UserRow[] }) {
  const p = useMemo(() => {
    const days: { jour: string; actions: number }[] = []
    const today = new Date()
    for (let i = 13; i >= 0; i--) {
      const d = new Date(today); d.setDate(today.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      days.push({ jour: `${d.getDate()}/${d.getMonth() + 1}`, actions: journal.filter((r) => r.horodatage?.slice(0, 10) === key).length })
    }
    const counts: Record<string, number> = {}
    journal.forEach((r) => { counts[r.action] = (counts[r.action] ?? 0) + 1 })
    const actions = Object.entries(counts).map(([a, n]) => ({ action: ACTION_LABEL[a] ?? a, n })).sort((a, b) => b.n - a.n).slice(0, 7)
    const roles: Record<string, number> = {}
    users.forEach((u) => { roles[u.role] = (roles[u.role] ?? 0) + 1 })
    const decisions = journal.filter((r) => r.action === 'decision_conciliation')
    const validees = decisions.filter((r) => r.decision_humaine?.startsWith('valid')).length
    const ia = journal.filter((r) => r.mode === 'ia').length
    const actifs = new Set(journal.filter((r) => r.utilisateur && Date.now() - new Date(r.horodatage).getTime() < 7 * 864e5).map((r) => r.utilisateur)).size
    return {
      days, actions, actifs,
      roles: Object.entries(roles).map(([r, n]) => ({ role: ROLE_LABEL[r] ?? r, n })),
      accord: decisions.length ? Math.round((validees / decisions.length) * 100) : null, nDecisions: decisions.length,
      partIA: journal.length ? Math.round((ia / journal.length) * 100) : 0,
    }
  }, [journal, users])

  return (
    <>
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { icon: Users, v: users.length, l: 'comptes vérifiés' },
          { icon: Activity, v: p.actifs, l: 'utilisateurs actifs (7 jours)' },
          { icon: BrainCircuit, v: `${p.partIA} %`, l: "des actions servies par l'IA générative" },
          { icon: Handshake, v: p.accord === null ? '—' : `${p.accord} %`, l: `accord humain avec l'IA (${p.nDecisions} décision(s))` },
        ].map(({ icon: Icon, v, l }) => (
          <Card key={l}><Icon size={20} className="text-gold-dark" /><div className="mt-2 font-display text-3xl font-bold text-navy-900">{v}</div><div className="text-xs text-slate-500">{l}</div></Card>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <SectionTitle sub="Chaque action tracée dans le journal d'audit.">Activité des 14 derniers jours</SectionTitle>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={p.days} margin={{ left: -20 }}>
              <defs><linearGradient id="pulse" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#c29a2e" stopOpacity={0.5} /><stop offset="100%" stopColor="#c29a2e" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="jour" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} /><Tooltip />
              <Area type="monotone" dataKey="actions" name="Actions" stroke="#c29a2e" strokeWidth={2} fill="url(#pulse)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <SectionTitle>Comptes par profil</SectionTitle>
          {p.roles.length === 0 ? <p className="text-sm text-slate-500">Aucun compte.</p> : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={p.roles} dataKey="n" nameKey="role" innerRadius={50} outerRadius={80} paddingAngle={3} label={(e) => String(e.name ?? '')}>
                  {p.roles.map((_, i) => <Cell key={i} fill={PIE[i % PIE.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
      <Card>
        <SectionTitle sub="Ce que les utilisateurs font réellement sur la plateforme.">Usages les plus fréquents</SectionTitle>
        <ResponsiveContainer width="100%" height={Math.max(120, p.actions.length * 38)}>
          <BarChart data={p.actions} layout="vertical" margin={{ left: 40 }}>
            <XAxis type="number" allowDecimals={false} fontSize={12} /><YAxis type="category" dataKey="action" width={170} fontSize={12} /><Tooltip />
            <Bar dataKey="n" name="Actions" fill="#0b2f5b" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </>
  )
}

function Overview() {
  const [s, setS] = useState<Awaited<ReturnType<typeof api.systeme>> | null>(null)
  const [users, setUsers] = useState<UserRow[]>([])
  const [journal, setJournal] = useState<JournalRow[]>([])
  const [run, setRun] = useState<string>('')
  const sendReminders = async () => {
    setRun('Envoi en cours…')
    try {
      const r = await api.rappels()
      setRun(r.webhook ? `${r.envoyes} rappel(s) envoyé(s), ${r.deja_envoyes} déjà envoyé(s) auparavant.` : 'Workflow de rappel non configuré.')
    } catch (e) { setRun((e as Error).message) }
  }
  useEffect(() => {
    api.systeme().then(setS).catch(() => {})
    api.utilisateurs().then(setUsers).catch(() => {})
    api.journal().then(setJournal).catch(() => {})
  }, [])
  if (!s) return <Spinner />
  const items = [
    { icon: Sparkles, label: 'IA générative', ok: s.llm.ia, detail: s.llm.ia ? `${s.llm.fournisseur ?? ''} · ${s.llm.modele ?? ''}` : s.llm.raison },
    { icon: Database, label: 'Base de données', ok: s.base === 'supabase', detail: s.base === 'supabase' ? 'Supabase (PostgreSQL)' : 'Mémoire locale (Supabase non configuré)' },
    { icon: Mail, label: 'E-mail OTP (n8n)', ok: s.n8n_otp, detail: s.n8n_otp ? 'Webhook configuré' : 'Non configuré : codes dans le journal serveur' },
    { icon: Mail, label: 'E-mail de bienvenue (n8n)', ok: s.n8n_bienvenue, detail: s.n8n_bienvenue ? 'Webhook configuré' : 'Non configuré' },
    { icon: BellRing, label: 'Rappels d\'échéance (n8n)', ok: s.n8n_rappels, detail: s.n8n_rappels ? 'J-15, J-7, J-3, J-1 · vérifié toutes les 6 h' : 'Non configuré' },
  ]
  return (
    <div className="space-y-6">
      <Title title="Vue d'ensemble" sub="Le pouls de la plateforme et l'état de ses services." />
      <Pulse journal={journal} users={users} />
      <div className="grid gap-4 md:grid-cols-2">
        {items.map(({ icon: Icon, label, ok, detail }) => (
          <Card key={label} className="flex items-center gap-4">
            <div className={clsx('flex h-11 w-11 items-center justify-center rounded-2xl', ok ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600')}><Icon size={22} /></div>
            <div className="flex-1"><div className="font-semibold text-navy-900">{label}</div><div className="text-sm text-slate-500">{detail}</div></div>
            {ok ? <CheckCircle2 className="text-emerald-500" /> : <XCircle className="text-amber-500" />}
          </Card>
        ))}
      </div>
      <div className="grid gap-4">
        <Card>
          <SectionTitle sub="Les rappels partent aussi automatiquement toutes les 6 heures.">Rappels d'échéance par e-mail</SectionTitle>
          <Button variant="gold" onClick={sendReminders}><BellRing size={16} /> Envoyer les rappels dus maintenant</Button>
          {run && <p className="mt-3 text-sm text-slate-600">{run}</p>}
        </Card>
      </div>
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
