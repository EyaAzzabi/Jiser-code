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
  langue: 'fr' | 'ar'
  analyse_id: string | null
}

export interface DossierRow {
  affecte_a?: string | null
  affecte_a_moi?: boolean
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
  perimetre?: string
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
  affectation?: { agent_nom: string; agent_id: string } | null
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
  perimetre?: string
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

export type StatutCompte = 'en_attente' | 'actif' | 'refuse' | 'suspendu'

export interface Utilisateur {
  id: string
  email: string
  role: Role
  nom: string
  prenom: string
  fonction: string
  langue: string
  details: Record<string, unknown>
  statut: StatutCompte
  consentements?: Record<string, unknown>
  verification?: { soumis_le?: string | null; decision?: string | null; motif?: string | null; score?: number | null; validateur?: string | null }
}

export type Role = 'entreprise' | 'ministre' | 'chef_centre' | 'contentieux' | 'admin' | 'conseil' | 'verificateur'
export const ROLES_ADMINISTRATION: Role[] = ['ministre', 'chef_centre', 'contentieux']
export const ROLE_LABELS: Record<string, string> = {
  entreprise: "Chef d'entreprise", ministre: 'Ministre des Finances', chef_centre: 'Chef de centre régional (CRCI)',
  contentieux: 'Chargé(e) du contentieux', admin: 'Administrateur plateforme', conseil: 'Conseil fiscal', verificateur: 'Vérificateur',
}

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

export interface Controle { controle: string; statut: 'ok' | 'alerte' | 'echec'; detail: string }
export interface Piece { id: string; type: string; nom: string; mime: string; taille: number; cree_le: string }
export interface Demande {
  id: string; email: string; nom: string; prenom: string; role: Role; role_label: string; details: Record<string, unknown>
  verification: { pre_verification?: { controles: Controle[]; score: number; bloquant: boolean }; soumis_le?: string }
  attente_heures: number; pieces: Piece[]; cree_le: string
}

export interface Groupe { nb: number | null; montant: number | null; masque?: boolean }
export interface National {
  kpi: { dossiers_en_cours: number; montant_bloque: number; montant_recouvrable: number; dossiers_avec_vice: number; taux_recouvrement: number | null
    taux_annulation: number | null; taux_conciliation: number | null; duree_moyenne_mois: number | null; dossiers_clos: number }
  par_gouvernorat: (Groupe & { gouvernorat: string; recouvrable: number | null })[]
  par_motif: (Groupe & { motif: string })[]
  par_etape: (Groupe & { etape: string })[]
  flux_mensuel: { mois: string; entrees: number; sorties: number }[]
  activite: { analyses: number; reponses: number; messages: number; conciliations: number; questions_ia: number; total: number }
  k_anonymat: number
  options: { gouvernorats: string[]; motifs: string[]; etapes: string[] }
  genere_le: string
}
export interface Agent { id: string; nom: string; email: string; dossiers: number; montant: number }
export interface ConciliationAValider { id: string; dossier_id: string; reference: string; gouvernorat: string; montant_notifie: number
  montant_propose: number; propose_par: string; cree_le: string }

export interface Message { id: string; conversation_id: string; auteur_id: string; auteur_role: string; auteur_nom: string; contenu: string
  piece_nom?: string | null; piece_mime?: string | null; a_piece?: boolean; lu_par: string[]; cree_le: string }
export interface Conversation { id: string; reference: string; dossier_id: string | null; analyse_id: string | null; entreprise_nom: string
  gouvernorat: string; dernier_message_le: string; non_lus?: number; agent?: string | null
  dernier?: { auteur_nom: string; auteur_role: string; extrait: string; cree_le: string } | null; messages?: Message[] }
export interface AideIA { texte: string; points: string[]; mode: string }

export interface Acces { horodatage: string; reference: string; role: string; role_label: string; centre: string | null; action: string }
export interface ApercuIA { original: string; envoye_a_l_ia: string; remplacements: { jeton: string; categorie: string }[] }
export interface Traitement { traitement: string; finalite: string; donnees: string; base: string; duree: string; destinataires: string }

export interface ArticleLegal { id: string; code: string; article: string; text: string; code_name?: string }
export interface ChangementVeille { id: string; source: string; code: string; article_id: string; article: string; type: 'ajout' | 'modification' | 'abrogation'
  ancien: ArticleLegal | null; nouveau: ArticleLegal | null; detecte_le: string; simulation: boolean }
export interface EtatVeille {
  sources: Record<string, { empreinte?: string; verifie_le?: string; modifie_le?: string | null; statut?: string; articles?: number }>
  executions: { debut: string; fin?: string; declencheur: string; changements?: number
    resultats: { source: string; statut: string; articles?: number; changements?: number; detail?: string }[] }[]
  en_cours: { debut?: string; etape?: string; source?: string | null; declencheur?: string }
  en_attente: ChangementVeille[]
  sources_config: { id: string; code: string; type: string; nom: string; url: string }[]
  base: { code: string; nom: string; articles: number }[]
  embeddings: { modele: string | null; articles: number; calcule_le: string | null; disponible: boolean }
  prochaine_execution: string | null
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
  let res: Response
  try {
    // never hang silently (lost Wi-Fi, server unreachable): give up after 90 s, AI analyses included
    res = await fetch(path, { signal: AbortSignal.timeout(90_000), ...init, headers })
  } catch {
    throw new Error('Serveur injoignable : vérifiez votre connexion internet puis réessayez.')
  }
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
const put = (body: unknown): RequestInit => ({ ...post(body), method: 'PUT' })

/** Authenticated download (documents, exports): returns an object URL to open or save. */
export async function blobUrl(path: string): Promise<string> {
  const token = loadSession()?.token
  const res = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) throw new Error('Téléchargement impossible')
  return URL.createObjectURL(await res.blob())
}

export const fileToBase64 = (file: File) => new Promise<string>((resolve, reject) => {
  const r = new FileReader()
  r.onload = () => resolve(String(r.result).split(',')[1] ?? '')
  r.onerror = () => reject(new Error('Lecture du fichier impossible'))
  r.readAsDataURL(file)
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
  // one file, or several photos = the pages of one notification
  analyser: (file: File | File[], langue: string, endpoint = '/api/contribuable/analyser') => {
    const form = new FormData()
    if (Array.isArray(file)) file.forEach((f) => form.append('pages', f))
    else form.append('fichier', file)
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
  decision: (id: string, decision: 'validee' | 'refusee') =>
    request<{ ok: boolean; statut: string; message: string }>(`/api/admin/dossiers/${id}/decision`, post({ decision })),
  utilisateurs: () => request<(Utilisateur & { cree_le: string; derniere_connexion: string | null })[]>('/api/plateforme/utilisateurs'),
  journal: () =>
    request<{ horodatage: string; action: string; cible: string; recommandation: string; mode: string; decision_humaine: string; utilisateur?: string }[]>(
      '/api/plateforme/journal',
    ),
  systeme: () => request<{ llm: Status['llm']; base: string; n8n_otp: boolean; n8n_bienvenue: boolean; n8n_rappels: boolean
    n8n_notifications: boolean; recherche_hybride: boolean }>('/api/plateforme/systeme'),
  rappels: () => request<{ envoyes: number; deja_envoyes: number; webhook: boolean }>('/api/plateforme/rappels', { method: 'POST' }),
  baseJuridique: () => request<{ code: string; nom: string; articles: number; source: string }[]>('/api/plateforme/base-juridique'),
  recherche: (q: string) => request<ArticleRef[]>(`/api/plateforme/recherche-juridique?q=${encodeURIComponent(q)}`),
  referentiel: () => request<{ centres: string[]; centres_a: string[]; roles: Record<string, string> }>('/api/public/referentiel'),
}

export const comptesApi = {
  deposerPiece: (type: string, file: File) => fileToBase64(file).then((contenu) =>
    request<Piece>('/api/comptes/pieces', post({ type, nom: file.name, mime: file.type || 'application/pdf', contenu }))),
  soumettre: () => request<Utilisateur>('/api/comptes/soumettre', { method: 'POST' }),
  statut: () => request<Utilisateur & { pieces: Piece[]; controles: Controle[]; delai_heures: number }>('/api/comptes/statut'),
  demandes: () => request<Demande[]>('/api/comptes/demandes'),
  decider: (id: string, decision: 'valide' | 'refuse', motif = '') =>
    request<{ ok: boolean; statut: string }>(`/api/comptes/demandes/${id}/decision`, post({ decision, motif })),
  pieceUrl: (id: string) => blobUrl(`/api/comptes/pieces/${id}`),
}

export const pilotageApi = {
  national: (f: Record<string, string>) => request<National>(`/api/pilotage/national?${new URLSearchParams(f)}`),
  equipe: () => request<Agent[]>('/api/pilotage/equipe'),
  affecter: (dossier_id: string, agent_id: string) => request<{ ok: boolean }>('/api/pilotage/affectations', post({ dossier_id, agent_id })),
  aValider: () => request<ConciliationAValider[]>('/api/pilotage/conciliations-a-valider'),
  deciderConciliation: (id: string, decision: 'validee' | 'refusee', motif = '') =>
    request<{ ok: boolean }>(`/api/pilotage/conciliations/${id}/decision`, post({ decision, motif })),
}

export const messagerieApi = {
  conversations: () => request<Conversation[]>('/api/messagerie/conversations'),
  ouvrir: (analyse_id: string) => request<Conversation>('/api/messagerie/conversations', post({ analyse_id })),
  conversation: (id: string) => request<Conversation>(`/api/messagerie/conversations/${id}`),
  envoyer: (id: string, contenu: string, piece?: { nom: string; mime: string; contenu: string }) =>
    request<Message>(`/api/messagerie/conversations/${id}/messages`, post({ contenu, piece })),
  aide: (id: string, action: 'resume' | 'suggestion' | 'pieces') => request<AideIA>(`/api/messagerie/conversations/${id}/ia`, post({ action })),
  duDossier: (dossierId: string) => request<{ conversation: { id: string; reference: string } | null }>(`/api/messagerie/dossier/${dossierId}`),
  pieceUrl: (messageId: string) => blobUrl(`/api/messagerie/messages/${messageId}/piece`),
}

export const confidentialiteApi = {
  acces: () => request<Acces[]>('/api/confidentialite/acces'),
  exporter: () => blobUrl('/api/confidentialite/export'),
  supprimer: (confirmation: string) => request<{ ok: boolean }>('/api/confidentialite/suppression', post({ confirmation })),
  consentements: (analyse_ia: boolean, communications: boolean) =>
    request<{ ok: boolean; consentements: Record<string, unknown> }>('/api/confidentialite/consentements', put({ analyse_ia, communications })),
  apercuIA: (analyse_id?: string) => request<ApercuIA>(`/api/confidentialite/apercu-ia${analyse_id ? `?analyse_id=${analyse_id}` : ''}`),
  registre: () => request<{ responsable: string; loi: string; traitements: Traitement[] }>('/api/confidentialite/registre'),
}

export const veilleApi = {
  etat: () => request<EtatVeille>('/api/plateforme/veille'),
  lancer: () => request<{ ok: boolean; message: string }>('/api/plateforme/veille/lancer', post({})),
  simuler: () => request<ChangementVeille>('/api/plateforme/veille/simuler', { method: 'POST' }),
  decider: (id: string, decision: 'valide' | 'rejete', motif = '') =>
    request<{ ok: boolean; publie: boolean; message: string }>(`/api/plateforme/veille/changements/${id}/decision`, post({ decision, motif })),
  embeddings: () => request<{ ok: boolean; message: string }>('/api/plateforme/veille/embeddings', { method: 'POST' }),
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
