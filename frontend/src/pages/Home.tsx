import { AlertTriangle, ArrowRight, BadgeCheck, Bot, Building2, CheckCircle2, Clock, FileSearch, FileText, Gavel, Handshake, Landmark, Languages, Lock, PenLine, Quote, Scale, ScanText, ScrollText, ShieldCheck, Sparkles, UserCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, espaceDuRole, type ModelMetrics, type Session } from '../api'
import { asset } from '../apiBase'

function HeroMockup() {
  return (
    <div className="relative mx-auto w-full max-w-md">
      <div className="rounded-3xl bg-white p-6 shadow-2xl shadow-navy-950/40">
        <img src={asset('logo.png')} alt="JISER" className="mx-auto w-52" />
      </div>
      <div className="animate-float absolute -left-10 top-8 hidden w-56 rounded-2xl bg-white p-3 text-sm shadow-xl md:block">
        <div className="flex items-center gap-2 font-semibold text-rose-600"><AlertTriangle size={16} /> Vice de procédure</div>
        <div className="mt-1 text-xs text-slate-600">Vérification de 8,6 mois : maximum 6 mois (art. 40 CDPF)</div>
      </div>
      <div className="animate-float-slow absolute -right-8 bottom-24 hidden w-48 rounded-2xl bg-white p-3 shadow-xl md:block">
        <div className="text-xs text-slate-500">Score de solidité</div>
        <div className="font-display text-2xl font-bold text-gold">34 / 100</div>
        <div className="mt-1 h-1.5 rounded-full bg-slate-100"><div className="h-1.5 w-1/3 rounded-full bg-gold" /></div>
      </div>
      <div className="animate-float absolute -bottom-6 left-6 hidden items-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm shadow-xl md:flex">
        <Clock size={16} className="text-navy-800" /> <span className="text-slate-700">Réponse avant le <b>10/10</b> · 15 jours</span>
      </div>
    </div>
  )
}

function Stat({ value, label, note }: { value: string; label: string; note: string }) {
  return (
    <div className="px-4 text-center">
      <div className="font-display text-4xl font-bold text-gold">{value}</div>
      <div className="mt-1 font-medium text-white">{label}</div>
      <div className="mt-0.5 text-xs text-slate-400">{note}</div>
    </div>
  )
}

const RIVE_CONTRIBUABLE = [
  'Notification incompréhensible, pleine d\'articles de loi',
  'Délai de 45 jours souvent manqué → taxation d\'office',
  'Un avocat coûte cher, un comptable est débordé',
]
const RIVE_ADMIN = [
  'Des dossiers bloqués des années en conciliation et au tribunal',
  'Redressements annulés pour vice de procédure',
  'Aucun outil pour prioriser le stock de dossiers',
]

const PERSONAS = [
  { name: 'Sami', role: 'Gérant d\'une PME à Sfax', quote: 'J\'ai reçu 180 000 DT de redressement. En deux minutes, j\'ai compris ce qu\'on me reproche et ce que je peux contester.', icon: Building2 },
  { name: 'Leila', role: 'Conseillère fiscale, 40 clients', quote: 'Les articles, les délais et un premier brouillon : je passe mon temps sur l\'argumentation, pas sur la recherche.', icon: FileText },
  { name: 'Karim', role: 'Vérificateur, CRCI Sfax', quote: 'Je vérifie ma notification avant de l\'envoyer. Fini les redressements annulés pour une question de délai.', icon: UserCheck },
  { name: 'Nadia', role: 'Cheffe du contentieux, DGI', quote: 'Je sais quels dossiers traiter d\'abord, et lesquels régler à l\'amiable pour encaisser plus vite.', icon: Landmark },
]

const AI_FEATURES = [
  { icon: ScanText, t: 'Lit vos documents', d: 'Une photo ou un PDF de notification devient un dossier structuré, chef par chef.' },
  { icon: Languages, t: 'Explique en français ou en arabe', d: 'Chaque redressement reformulé simplement, dans la langue que vous choisissez.' },
  { icon: Bot, t: 'Répond à vos questions', d: "Un assistant qui cite les articles du CDPF, du Code de la TVA et de l'IRPP/IS." },
  { icon: PenLine, t: 'Rédige les réponses', d: "Brouillon d'opposition pour l'entreprise, motivations renforcées pour le vérificateur." },
  { icon: Gavel, t: 'Évalue chaque dossier', d: 'Score de solidité par modèle ML, expliqué facteur par facteur (SHAP).' },
  { icon: Handshake, t: 'Propose des conciliations', d: "Avis juridique, montant à proposer et projet de lettre, validés par l'agent." },
]

export default function Home({ onSignup, session }: { onSignup: () => void; session: Session | null }) {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null)
  const [articles, setArticles] = useState<number | null>(null)
  const navigate = useNavigate()
  const go = (target: string) => (session ? navigate(espaceDuRole(session.role)) : navigate(target))
  useEffect(() => {
    api.chiffres().then((c) => { setMetrics(c.modele); setArticles(c.articles) }).catch(() => {})
  }, [])

  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden bg-gradient-to-br from-navy-950 via-navy-900 to-navy-700 text-white">
        <svg className="pointer-events-none absolute -bottom-24 left-0 w-full opacity-15" viewBox="0 0 1200 300" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 300 C 300 40, 900 40, 1200 300" fill="none" stroke="#c29a2e" strokeWidth="6" />
          <path d="M0 300 C 320 90, 880 90, 1200 300" fill="none" stroke="#2f74c0" strokeWidth="18" />
        </svg>
        <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 py-20 lg:grid-cols-2">
          <div className="animate-fade-up">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-gold ring-1 ring-gold/40">
              <Sparkles size={14} /> IA · Conseil · Solution
            </div>
            <h1 className="mt-5 text-4xl font-bold leading-tight md:text-5xl">
              Le <span className="text-gold">pont</span> entre le contribuable et l'administration fiscale.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-200">
              JISER accompagne chaque dossier de redressement, de la notification à la conciliation : compris en deux minutes
              par l'entreprise, solide et prioritaire pour l'administration.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button onClick={() => go('/entreprise')} className="flex items-center gap-2 rounded-xl bg-gold px-6 py-3.5 font-semibold text-white shadow-lg shadow-gold/30 transition hover:bg-gold-dark">
                <Building2 size={18} /> J'ai reçu une notification <ArrowRight size={16} />
              </button>
              <button onClick={() => go('/administration')} className="flex items-center gap-2 rounded-xl bg-white/10 px-6 py-3.5 font-semibold text-white ring-1 ring-white/30 transition hover:bg-white/20">
                <Landmark size={18} /> Espace administration
              </button>
            </div>
            {!session && (
              <button onClick={onSignup} className="mt-5 text-sm text-slate-300 underline decoration-gold underline-offset-4 hover:text-white">
                Créez votre espace sécurisé en quelques minutes
              </button>
            )}
          </div>
          <HeroMockup />
        </div>
      </section>

      {/* STATS */}
      <section className="bg-navy-950 py-10">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 md:grid-cols-4">
          <Stat value="45 j" label="pour répondre à une notification" note="Art. 43 et 44 du CDPF, édition officielle 2024" />
          <Stat value={articles ? String(articles) : '274'} label="articles de loi indexés" note="CDPF, Code TVA, Code IRPP/IS" />
          <Stat value="76 %" label="des pays de l'OCDE utilisent l'IA" note="dans le contrôle fiscal (OCDE, 2025)" />
          <Stat value={metrics ? `+${Math.round(metrics.triage.gain_vs_fifo_pct)} %` : '+269 %'} label="recouvré grâce au tri JISER" note="vs traitement par ancienneté, à capacité égale" />
        </div>
      </section>

      {/* TWO BANKS, ONE BRIDGE */}
      <section className="mx-auto max-w-7xl px-4 py-20">
        <div className="text-center">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Le problème</div>
          <h2 className="mt-2 text-3xl font-bold text-navy-900">Deux rives qui ne se comprennent pas</h2>
          <p className="mx-auto mt-3 max-w-2xl text-slate-600">Pendant ce temps, les dossiers s'accumulent et l'État n'encaisse rien.</p>
        </div>
        <div className="mt-12 grid items-center gap-6 lg:grid-cols-[1fr_auto_1fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
            <div className="flex items-center gap-2 text-navy-900"><Building2 className="text-bridge" /> <span className="text-lg font-semibold">Côté entreprise</span></div>
            <ul className="mt-4 space-y-3">{RIVE_CONTRIBUABLE.map((t) => <li key={t} className="flex gap-2 text-slate-600"><AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-400" />{t}</li>)}</ul>
          </div>
          <div className="flex flex-col items-center px-2">
            <svg viewBox="0 0 160 90" className="w-40" aria-hidden="true">
              <path d="M5 80 C 40 10, 120 10, 155 80" fill="none" stroke="#0b2f5b" strokeWidth="9" strokeLinecap="round" />
              <path d="M22 80 C 55 35, 105 35, 138 80" fill="none" stroke="#2f74c0" strokeWidth="6" strokeLinecap="round" />
              <circle cx="80" cy="22" r="7" fill="#c29a2e" />
            </svg>
            <div className="mt-1 font-display font-bold text-navy-900">JISER</div>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
            <div className="flex items-center gap-2 text-navy-900"><Landmark className="text-bridge" /> <span className="text-lg font-semibold">Côté administration</span></div>
            <ul className="mt-4 space-y-3">{RIVE_ADMIN.map((t) => <li key={t} className="flex gap-2 text-slate-600"><AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-400" />{t}</li>)}</ul>
          </div>
        </div>
      </section>

      {/* AI */}
      <section className="bg-gradient-to-b from-canvas to-white py-20">
        <div className="mx-auto max-w-7xl px-4">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-gold"><Sparkles size={14} /> Intelligence artificielle</div>
            <h2 className="mt-2 text-3xl font-bold text-navy-900">Ce que fait l'IA de JISER</h2>
            <p className="mx-auto mt-3 max-w-2xl text-slate-600">Un modèle de langage pour lire, expliquer et rédiger ; un modèle de machine learning pour évaluer et prioriser ; les règles du CDPF pour vérifier.</p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {AI_FEATURES.map(({ icon: Icon, t, d }) => (
              <div key={t} className="group rounded-3xl border border-gold/30 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-gold to-gold-dark text-white shadow"><Icon size={22} /></div>
                <h3 className="mt-4 text-lg font-semibold text-navy-900">{t}</h3>
                <p className="mt-1 text-sm text-slate-600">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="solution" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4">
          <div className="text-center">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">La solution</div>
            <h2 className="mt-2 text-3xl font-bold text-navy-900">Comment fonctionne JISER</h2>
          </div>
          <div className="relative mt-12 grid gap-6 md:grid-cols-4">
            <div className="absolute left-0 right-0 top-8 hidden h-0.5 bg-gradient-to-r from-bridge via-gold to-bridge md:block" />
            {[
              { icon: FileSearch, t: 'Lire', d: 'La notification (PDF ou photo) est lue et découpée chef par chef.' },
              { icon: Scale, t: 'Vérifier', d: 'Chaque règle de procédure du CDPF est contrôlée : délais, durée, motivation.' },
              { icon: Gavel, t: 'Évaluer', d: 'Un modèle estime la solidité de chaque chef et explique pourquoi.' },
              { icon: ScrollText, t: 'Résoudre', d: 'Brouillon de réponse pour l\'entreprise, conciliation pour l\'administration.' },
            ].map(({ icon: Icon, t, d }, i) => (
              <div key={t} className="relative text-center">
                <div className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-900 text-white shadow-lg ring-4 ring-white">
                  <Icon size={26} />
                  <span className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-gold text-xs font-bold">{i + 1}</span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-navy-900">{t}</h3>
                <p className="mt-1 text-sm text-slate-600">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TWO SPACES */}
      <section className="mx-auto max-w-7xl px-4 py-20">
        <div className="grid gap-6 lg:grid-cols-2">
          {[
            { to: '/entreprise', icon: Building2, t: 'Pour les entreprises et leurs conseils', items: ['Chaque chef expliqué en langage simple', 'Contestabilité 🟢 🟠 🔴 et vices de procédure', 'Articles de loi cités et pièces à rassembler', 'Compte à rebours et brouillon de réponse'], cta: 'Analyser une notification' },
            { to: '/administration', icon: Landmark, t: 'Pour l\'administration fiscale', items: ['Contrôle qualité avant l\'envoi d\'une notification', 'Score de solidité expliqué (SHAP) par dossier', 'Stock trié par montant recouvrable', 'Proposition de conciliation et tableau de bord'], cta: 'Ouvrir le stock de dossiers' },
          ].map(({ to, icon: Icon, t, items, cta }) => (
            <div key={to} className="group rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-bridge-light text-navy-900"><Icon /></div>
              <h3 className="mt-4 text-xl font-bold text-navy-900">{t}</h3>
              <ul className="mt-4 space-y-2">{items.map((it) => <li key={it} className="flex gap-2 text-slate-600"><CheckCircle2 size={18} className="mt-0.5 shrink-0 text-gold" />{it}</li>)}</ul>
              <button onClick={() => go(to)} className="mt-6 inline-flex items-center gap-2 font-semibold text-navy-900 group-hover:text-gold-dark">{cta} <ArrowRight size={16} /></button>
            </div>
          ))}
        </div>
      </section>

      {/* PERSONAS */}
      <section id="pour-qui" className="bg-gradient-to-b from-white to-canvas py-20">
        <div className="mx-auto max-w-7xl px-4">
          <div className="text-center">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Pour qui</div>
            <h2 className="mt-2 text-3xl font-bold text-navy-900">Chacun traverse le pont à sa façon</h2>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {PERSONAS.map(({ name, role, quote, icon: Icon }) => (
              <div key={name} className="flex flex-col rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <Quote className="text-gold" size={22} />
                <p className="mt-3 flex-1 text-sm leading-relaxed text-slate-700">« {quote} »</p>
                <div className="mt-5 flex items-center gap-3 border-t border-slate-100 pt-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-navy-900 text-white"><Icon size={18} /></div>
                  <div><div className="font-semibold text-navy-900">{name}</div><div className="text-xs text-slate-500">{role}</div></div>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-slate-400">Personas illustratifs.</p>
        </div>
      </section>

      {/* TRUST */}
      <section className="mx-auto max-w-7xl px-4 py-20">
        <div className="grid items-center gap-10 rounded-3xl bg-navy-900 p-10 text-white lg:grid-cols-2">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Confiance</div>
            <h2 className="mt-2 text-3xl font-bold">Une IA explicable, sous contrôle humain</h2>
            <p className="mt-3 text-slate-300">JISER ne décide jamais à la place de l'agent ou du contribuable. Il recommande, explique et cite ses sources.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              { icon: UserCheck, t: 'L\'humain décide' },
              { icon: BadgeCheck, t: 'Articles de loi cités' },
              { icon: ShieldCheck, t: 'Journal de chaque recommandation' },
              { icon: Lock, t: 'Loi organique 2004-63 respectée' },
            ].map(({ icon: Icon, t }) => (
              <div key={t} className="flex items-center gap-3 rounded-2xl bg-white/10 p-4"><Icon className="text-gold" /> <span className="font-medium">{t}</span></div>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="pb-20 text-center">
        <h2 className="text-3xl font-bold text-navy-900">Prêt à traverser le pont ?</h2>
        <p className="mt-2 text-slate-600">Créez votre espace en quelques minutes, sécurisé par un code envoyé à votre e-mail.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {session ? (
            <button onClick={() => navigate(espaceDuRole(session.role))} className="flex items-center gap-2 rounded-xl bg-navy-900 px-6 py-3.5 font-semibold text-white hover:bg-navy-800">Accéder à mon espace <ArrowRight size={16} /></button>
          ) : (
            <button onClick={onSignup} className="flex items-center gap-2 rounded-xl bg-gold px-6 py-3.5 font-semibold text-white hover:bg-gold-dark">Créer mon espace <ArrowRight size={16} /></button>
          )}
        </div>
      </section>
    </div>
  )
}
