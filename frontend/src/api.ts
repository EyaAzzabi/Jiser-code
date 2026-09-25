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
  }
  par_gouvernorat: { gouvernorat: string; nb: number; montant: number; recouvrable: number }[]
  par_etape: { etape: string; nb: number; montant: number }[]
  par_type: { type: string; montant: number }[]
  causes_annulation: { cause: string; nb: number }[]
  modele: ModelMetrics | null
}

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
  llm: { ia: boolean; modele?: string; raison?: string }
  articles: number
  dossiers: number
  date_demo: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep status text */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  status: () => request<Status>('/api/status'),
  exemples: () => request<{ nom: string; fichier: string }[]>('/api/exemples'),
  exempleBlob: async (fichier: string) => {
    const res = await fetch(`/api/exemples/${fichier}`)
    if (!res.ok) throw new Error('Exemple introuvable')
    return new File([await res.blob()], fichier, { type: 'application/pdf' })
  },
  analyser: (file: File, endpoint = '/api/contribuable/analyser') => {
    const form = new FormData()
    form.append('fichier', file)
    return request<Analyse>(endpoint, { method: 'POST', body: form })
  },
  brouillon: (analyse: Analyse, signataire: string) =>
    request<{ lettre: string; mode: string }>('/api/contribuable/brouillon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analyse, signataire }),
    }),
  dossiers: (params: Record<string, string>) =>
    request<Triage>(`/api/admin/dossiers?${new URLSearchParams(params)}`),
  dossier: (id: string) => request<DossierDetail>(`/api/admin/dossiers/${id}`),
  dashboard: () => request<Dashboard>('/api/admin/tableau-de-bord'),
  utilisateurs: () => request<{ nom: string; role: string; structure: string }[]>('/api/plateforme/utilisateurs'),
  journal: () =>
    request<{ horodatage: string; action: string; cible: string; recommandation: string; mode: string; decision_humaine: string }[]>(
      '/api/plateforme/journal',
    ),
  baseJuridique: () => request<{ code: string; nom: string; articles: number; source: string }[]>('/api/plateforme/base-juridique'),
  recherche: (q: string) => request<ArticleRef[]>(`/api/plateforme/recherche-juridique?q=${encodeURIComponent(q)}`),
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

// ---- Authentification (OTP) -----------------------------------------------------------------

export interface OtpDemande {
  destination_masquee: string
  expire_dans_s: number
  renvoi_dans_s: number
  tentatives_max: number
  code_demo?: string
}

export interface SessionInfo {
  token: string
  profil: { role: string; nom: string; prenom: string; details: Record<string, unknown>; contact: string }
}

const json = (body: unknown, token?: string): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  body: JSON.stringify(body),
})

export const authApi = {
  demanderOtp: (canal: 'sms' | 'email', destination: string) =>
    request<OtpDemande>('/api/auth/otp/demander', json({ canal, destination })),
  verifierOtp: (canal: 'sms' | 'email', destination: string, code: string) =>
    request<{ token: string }>('/api/auth/otp/verifier', json({ canal, destination, code })),
  enregistrerProfil: (token: string, profil: Record<string, unknown>) =>
    request<{ ok: boolean; profil: SessionInfo['profil'] }>('/api/auth/profil', json(profil, token)),
  deconnexion: (token: string) => request<{ ok: boolean }>('/api/auth/deconnexion', json({}, token)),
}

export function loadSession(): SessionInfo | null {
  try {
    const raw = sessionStorage.getItem('jiser-session')
    return raw ? (JSON.parse(raw) as SessionInfo) : null
  } catch {
    return null
  }
}

export function saveSession(s: SessionInfo | null) {
  try {
    if (s) sessionStorage.setItem('jiser-session', JSON.stringify(s))
    else sessionStorage.removeItem('jiser-session')
  } catch {
    /* storage unavailable: session lives in memory only */
  }
}
