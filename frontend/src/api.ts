// Types mirror backend/app/schemas.py and the admin endpoints.

export type Contestabilite = 'solide' | 'discutable' | 'contestable'

export interface Entreprise {
  nom: string
  matricule_fiscal: string
  secteur: string
  taille: 'TPE' | 'PME' | 'GE'
  gouvernorat: string
}

export interface Chef {
  id: string
  type: string
  libelle: string
  impot: string
  exercice: number
  montant_principal: number
  penalites: number
  article_invoque: string | null
  motivation: string
  motivation_qualite: 'detaillee' | 'sommaire' | 'absente'
  methode: string
}

export interface Notification {
  reference: string
  centre: string
  type_verification: 'approfondie' | 'preliminaire'
  comptabilite_conforme: boolean
  date_avis: string | null
  date_debut_verification: string | null
  date_notification: string
  exercices_verifies: number[]
  entreprise: Entreprise
  chefs: Chef[]
}

export interface ArticleRef {
  id: string
  code: string
  article: string
  extrait: string
  source_url: string
}

export interface ProcedureCheck {
  code: string
  label: string
  article: string
  statut: 'ok' | 'vice' | 'a_verifier'
  detail: string
}

export interface ChefAnalyse {
  chef: Chef
  explication: string
  contestabilite: Contestabilite
  arguments: string[]
  pieces_a_fournir: string[]
  articles: ArticleRef[]
}

export interface Analyse {
  notification: Notification
  montant_total: number
  date_limite_reponse: string
  jours_restants: number
  procedure: ProcedureCheck[]
  chefs: ChefAnalyse[]
  resume: string
  montant_contestable: number
  mode: 'ia' | 'hors_ligne'
  langue: 'fr' | 'derja'
  analyse_id: string | null
}

export interface DossierRow {
  id: string
  reference: string
  entreprise: string
  gouvernorat: string
  taille: string
  etape: string
  date_notification: string
  anciennete_jours: number
  montant_total: number
  montant_recouvrable: number
  score_solidite: number
  priorite: number
  vices: string[]
  groupe: string
  nb_chefs: number
}

export interface Triage {
  total: number
  montant_total: number
  montant_recouvrable: number
  groupes: { groupe: string; nb: number; montant: number }[]
  dossiers: DossierRow[]
}

export interface ConciliationItem {
  chef_id: string
  libelle: string
  montant: number
  p_maintenu: number
  part_recouvrable: number
  action: 'maintenir' | 'transiger' | 'abandonner'
  montant_propose: number
  justification: string
}

export interface DossierDetail {
  dossier: {
    id: string
    etape: string
    pieces_fournies_ratio: number
    reponse_contribuable: boolean
    notification: Notification & { montant_total?: number }
  }
  score: {
    score_solidite: number
    proba_maintien: number
    montant_recouvrable_estime: number
    explications: { facteur: string; impact: number }[]
  }
  procedure: ProcedureCheck[]
  conciliation: {
    items: ConciliationItem[]
    montant_notifie: number
    montant_propose: number
    montant_attendu_contentieux: number
    commentaire: string
  }
}

export interface Dashboard {
  kpi: {
    dossiers_en_cours: number
    montant_bloque: number
    montant_recouvrable_estime: number
    dossiers_avec_vice: number
    taux_recouvrement_historique: number
    taux_chefs_annules: number
    duree_moyenne_mois: number
    taux_conciliation: number
  }
  par_gouvernorat: { gouvernorat: string; nb: number; montant: number; recouvrable: number }[]
  par_etape: { etape: string; nb: number; montant: number }[]
  par_type: { type: string; montant: number }[]
  causes_annulation: { cause: string; nb: number }[]
  motifs: { motif: string; nb: number }[]
  serie_mensuelle: { mois: string; notifies: number; clotures: number }[]
  modele: ModelMetrics | null
}

export interface AiMode { mode: 'ia' | 'hors_ligne' }
export interface Synthese extends AiMode { synthese: string; actions: { titre: string; detail: string }[] }
export interface AvisDossier extends AiMode { avis: string; points_forts: string[]; points_faibles: string[]; lettre_conciliation: string }
export interface Ameliorations extends AiMode { ameliorations: { chef_id: string; probleme: string; motivation_proposee: string }[] }
export type ConciliationRow = DossierRow & { montant_propose: number; montant_attendu_contentieux: number; gain_immediat: number }

export interface ModelMetrics {
  n_dossiers_train: number
  n_dossiers_test: number
  auc_chef_maintenu: number
  auc_dossier_recouvre_50pct: number
  mae_taux_recouvrement: number
  triage: {
    capacite: string
    recouvre_jiser: number
    recouvre_fifo: number
    recouvre_plus_gros_montants: number
    gain_vs_fifo_pct: number
    gain_vs_plus_gros_pct: number
  }
  note: string
}

export interface Status {
  ok: boolean
  llm: { ia: boolean; fournisseur?: string; modele?: string; raison?: string }
  articles: number
  base: string
  date: string
}

export interface Utilisateur {
  id: string
  email: string
  role: Role
  nom: string
  prenom: string
  fonction: string
  langue: string
  details: Record<string, unknown>
}

export type Role = 'entreprise' | 'conseil' | 'verificateur' | 'contentieux' | 'admin'

export interface Session {
  token: string
  role: Role | null
  utilisateur: Utilisateur | null
}

export interface OtpDemande {
  destination_masquee: string
  expire_dans_s: number
  renvoi_dans_s: number
  tentatives_max: number
  livraison: 'email' | 'journal_serveur'
}

export interface AnalyseResume {
  id: string
  reference: string
  entreprise: string
  montant_total: number
  montant_contestable: number
  date_limite: string
  nb_vices: number
  cree_le: string
  jours_restants: number
}

export interface Reponse {
  id: string
  analyse_id: string
  lettre: string
  mode: string
  cree_le: string
}

export interface AssistantAnswer {
  reponse: string
  articles: ArticleRef[]
  suggestions: string[]
  mode: 'ia' | 'hors_ligne'
}

// ---- Session (sessionStorage: cleared when the browser tab closes) ---------------------------

let current: Session | null = null
const listeners = new Set<(s: Session | null) => void>()

export function loadSession(): Session | null {
  if (current) return current
  try {
    const raw = sessionStorage.getItem('jiser-session')
    current = raw ? (JSON.parse(raw) as Session) : null
  } catch {
    current = null
  }
  return current
}

export function saveSession(s: Session | null) {
  current = s
  try {
    if (s) sessionStorage.setItem('jiser-session', JSON.stringify(s))
    else sessionStorage.removeItem('jiser-session')
  } catch {
    /* storage unavailable: session kept in memory */
  }
  listeners.forEach((fn) => fn(s))
}

export function onSessionChange(fn: (s: Session | null) => void) {
  listeners.add(fn)
  return () => { listeners.delete(fn) }
}

// ---- HTTP -----------------------------------------------------------------------------------

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = loadSession()?.token
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep status text */
    }
    if (res.status === 401 && token) saveSession(null)   // expired session: back to login
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const post = (body: unknown): RequestInit => ({
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})

export const api = {
  status: () => request<Status>('/api/status'),
  chiffres: () => request<{ articles: number; modele: ModelMetrics | null }>('/api/public/chiffres'),
  exemples: () => request<{ nom: string; fichier: string }[]>('/api/exemples'),
  exempleBlob: async (fichier: string) => {
    const token = loadSession()?.token
    const res = await fetch(`/api/exemples/${fichier}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!res.ok) throw new Error('Exemple introuvable')
    return new File([await res.blob()], fichier, { type: 'application/pdf' })
  },
  analyser: (file: File, langue: string, endpoint = '/api/contribuable/analyser') => {
    const form = new FormData()
    form.append('fichier', file)
    form.append('langue', langue)
    return request<Analyse>(endpoint, { method: 'POST', body: form })
  },
  analyses: () => request<AnalyseResume[]>('/api/contribuable/analyses'),
  analyse: (id: string, langue?: string) =>
    request<Analyse>(`/api/contribuable/analyses/${id}${langue ? `?langue=${langue}` : ''}`),
  brouillon: (analyse_id: string, signataire: string) =>
    request<{ lettre: string; mode: string }>('/api/contribuable/brouillon', post({ analyse_id, signataire })),
  reponses: () => request<Reponse[]>('/api/contribuable/reponses'),
  assistant: (question: string, langue: string, historique: { role: string; texte: string }[], analyse_id?: string) =>
    request<AssistantAnswer>('/api/contribuable/assistant', post({ question, langue, historique, analyse_id })),
  dossiers: (params: Record<string, string>) =>
    request<Triage>(`/api/admin/dossiers?${new URLSearchParams(params)}`),
  dossier: (id: string) => request<DossierDetail>(`/api/admin/dossiers/${id}`),
  dashboard: () => request<Dashboard>('/api/admin/tableau-de-bord'),
  syntheseIA: () => request<Synthese>('/api/admin/synthese-ia'),
  avisIA: (id: string) => request<AvisDossier>(`/api/admin/dossiers/${id}/avis-ia`),
  ameliorer: (a: Analyse) => request<Ameliorations>('/api/admin/ameliorer-notification', post(a)),
  conciliations: () => request<ConciliationRow[]>('/api/admin/conciliations'),
  decision: (id: string, decision: 'validee' | 'refusee') => request<{ ok: boolean }>(`/api/admin/dossiers/${id}/decision`, post({ decision })),
  utilisateurs: () => request<(Utilisateur & { cree_le: string; derniere_connexion: string | null })[]>('/api/plateforme/utilisateurs'),
  journal: () =>
    request<{ horodatage: string; action: string; cible: string; recommandation: string; mode: string; decision_humaine: string; utilisateur?: string }[]>(
      '/api/plateforme/journal',
    ),
  systeme: () => request<{ llm: Status['llm']; base: string; n8n_otp: boolean; n8n_bienvenue: boolean; n8n_rappels: boolean }>('/api/plateforme/systeme'),
  rappels: () => request<{ envoyes: number; deja_envoyes: number; webhook: boolean }>('/api/plateforme/rappels', { method: 'POST' }),
  baseJuridique: () => request<{ code: string; nom: string; articles: number; source: string }[]>('/api/plateforme/base-juridique'),
  recherche: (q: string) => request<ArticleRef[]>(`/api/plateforme/recherche-juridique?q=${encodeURIComponent(q)}`),
}

export const authApi = {
  demanderOtp: (email: string, intention: 'inscription' | 'connexion' | 'admin') =>
    request<OtpDemande>('/api/auth/otp/demander', post({ email, intention })),
  verifierOtp: (email: string, code: string) =>
    request<{ token: string; role: Role | null; utilisateur: Utilisateur | null }>('/api/auth/otp/verifier', post({ email, code })),
  enregistrerProfil: (profil: Record<string, unknown>) =>
    request<{ ok: boolean; utilisateur: Utilisateur }>('/api/auth/profil', post(profil)),
  deconnexion: () => request<{ ok: boolean }>('/api/auth/deconnexion', { method: 'POST' }),
}

export const dt = (n: number) =>
  new Intl.NumberFormat('fr-TN', { maximumFractionDigits: 0 }).format(Math.round(n)) + ' DT'

export const mdt = (n: number) =>
  n >= 1e6 ? `${(n / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} MDT` : dt(n)

export const frDate = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('fr-FR') : '—')

const CODE_NAMES: Record<string, string> = { cdpf: 'CDPF', ctva: 'Code TVA', cirppis: 'Code IRPP/IS' }

// "cdpf-art-44-bis" -> "Art. 44 bis CDPF"
export const articleLabel = (id: string) => {
  const [code, num = ''] = id.split('-art-')
  return `Art. ${num.replace(/-/g, ' ')} ${CODE_NAMES[code] ?? code}`
}

export const espaceDuRole = (role: Role | null | undefined) =>
  role === 'entreprise' || role === 'conseil' ? '/entreprise' : role === 'admin' ? '/plateforme' : role ? '/administration' : '/'
