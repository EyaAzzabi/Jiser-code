import { Briefcase, Building2, Landmark, Settings, UserCheck, type LucideIcon } from 'lucide-react'

export type Role = 'entreprise' | 'conseil' | 'verificateur' | 'contentieux' | 'admin'

export type FieldType = 'text' | 'select' | 'number' | 'date' | 'multi' | 'toggle'

export interface Field {
  key: string
  label: string
  type: FieldType
  required?: boolean
  options?: string[]
  placeholder?: string
  help?: string
  pattern?: RegExp
  patternMessage?: string
  showIf?: (values: Record<string, unknown>) => boolean
  full?: boolean
}

export interface Section {
  title: string
  subtitle: string
  fields: Field[]
}

export interface RoleConfig {
  id: Role
  label: string
  who: string
  icon: LucideIcon
  to: string
  sections: Section[]
  parcours: string[]
}

export const GOUVERNORATS = ['Tunis', 'Ariana', 'Ben Arous', 'Manouba', 'Nabeul', 'Zaghouan', 'Bizerte', 'Béja', 'Jendouba', 'Le Kef',
  'Siliana', 'Sousse', 'Monastir', 'Mahdia', 'Sfax', 'Kairouan', 'Kasserine', 'Sidi Bouzid', 'Gabès', 'Médenine', 'Tataouine',
  'Gafsa', 'Tozeur', 'Kébili']
const SECTEURS = ['Commerce de gros', 'Commerce de détail', 'BTP', 'Industrie textile', 'Agroalimentaire', 'Services informatiques',
  'Transport et logistique', 'Promotion immobilière', 'Tourisme et hôtellerie', 'Professions libérales', 'Autre']
const IMPOTS = ['TVA', 'Impôt sur les sociétés', 'IRPP', 'Retenue à la source', "Droits d'enregistrement"]

export const MATRICULE_RE = /^\d{7}[A-Z]\/[A-Z]\/[A-Z]\/\d{3}$/

export const ROLES: RoleConfig[] = [
  {
    id: 'entreprise', label: "Chef d'entreprise", who: "J'ai reçu une notification de redressement", icon: Building2, to: '/entreprise',
    parcours: ['Déposez votre notification (PDF ou photo)', "Lisez ce qu'on vous reproche, chef par chef, en clair", 'Générez un brouillon de réponse avant la date limite'],
    sections: [
      {
        title: 'Votre entreprise', subtitle: 'Ces informations pré-remplissent vos réponses et vérifient que la notification vous concerne.',
        fields: [
          { key: 'raison_sociale', label: 'Raison sociale', type: 'text', required: true, placeholder: 'Société Distribution El Amen SARL', full: true },
          { key: 'matricule_fiscal', label: 'Matricule fiscal', type: 'text', required: true, placeholder: '1234567A/A/M/000',
            pattern: MATRICULE_RE, patternMessage: 'Format attendu : 7 chiffres, une lettre, puis /A/M/000 (ex. 1478523K/A/M/000)',
            help: 'Figure sur votre carte d\'identification fiscale et sur la notification.' },
          { key: 'forme_juridique', label: 'Forme juridique', type: 'select', required: true, options: ['SARL', 'SUARL', 'SA', 'SNC', 'Entreprise individuelle', 'Autre'] },
          { key: 'secteur', label: "Secteur d'activité", type: 'select', required: true, options: SECTEURS },
          { key: 'gouvernorat', label: 'Gouvernorat du siège', type: 'select', required: true, options: GOUVERNORATS },
          { key: 'effectif', label: 'Effectif', type: 'select', required: true, options: ['1 à 9', '10 à 49', '50 à 199', '200 et plus'] },
          { key: 'chiffre_affaires', label: "Chiffre d'affaires annuel", type: 'select', options: ['< 300 000 DT', '300 000 à 1 M DT', '1 à 10 M DT', '> 10 M DT'] },
        ],
      },
      {
        title: 'Votre situation fiscale', subtitle: 'Pour calculer vos délais et adapter les conseils à votre dossier.',
        fields: [
          { key: 'regime', label: "Régime d'imposition", type: 'select', required: true, options: ['Réel', 'Forfaitaire'] },
          { key: 'centre', label: 'Centre de rattachement', type: 'select', options: ['Centre régional de contrôle des impôts', 'Direction des grandes entreprises', 'Je ne sais pas'] },
          { key: 'situation', label: 'Où en êtes-vous ?', type: 'select', options: ["J'ai reçu une notification de redressement", 'Une vérification est en cours', "J'ai reçu un arrêté de taxation d'office", 'Je me renseigne'], full: true },
          { key: 'date_notification', label: 'Date de réception de la notification', type: 'date',
            help: 'Vous avez 30 jours à compter de cette date pour répondre (art. 44 CDPF).',
            showIf: (v) => String(v.situation ?? '').startsWith("J'ai reçu") },
          { key: 'montant_notifie', label: 'Montant réclamé (DT)', type: 'number', placeholder: '180000',
            showIf: (v) => String(v.situation ?? '').startsWith("J'ai reçu") },
          { key: 'impots_concernes', label: 'Impôts concernés', type: 'multi', options: IMPOTS, full: true },
          { key: 'conseil_fiscal', label: 'Êtes-vous accompagné par un conseil ?', type: 'select', options: ['Oui', 'Non', 'Je cherche un conseil'] },
          { key: 'nom_conseil', label: 'Nom du conseil / cabinet', type: 'text', showIf: (v) => v.conseil_fiscal === 'Oui' },
        ],
      },
    ],
  },
  {
    id: 'conseil', label: 'Conseil fiscal / comptable', who: "J'accompagne des entreprises", icon: Briefcase, to: '/entreprise',
    parcours: ['Analysez la notification de votre client', 'Vérifiez les vices de procédure et les articles cités', 'Partez du brouillon de réponse et complétez-le'],
    sections: [
      {
        title: 'Votre cabinet', subtitle: "Votre qualité professionnelle est vérifiée avant l'accès aux dossiers de vos clients.",
        fields: [
          { key: 'cabinet', label: 'Nom du cabinet', type: 'text', required: true, full: true },
          { key: 'profession', label: 'Profession', type: 'select', required: true, options: ['Expert-comptable', 'Conseiller fiscal', 'Avocat', 'Comptable'] },
          { key: 'numero_inscription', label: "N° d'inscription à l'ordre", type: 'text', required: true,
            help: 'Ordre des experts-comptables, Ordre des conseillers fiscaux ou Barreau.' },
          { key: 'gouvernorat', label: 'Gouvernorat', type: 'select', required: true, options: GOUVERNORATS },
          { key: 'taille_cabinet', label: 'Taille du cabinet', type: 'select', options: ['Indépendant', '2 à 5 personnes', '6 à 20 personnes', 'Plus de 20'] },
        ],
      },
      {
        title: 'Votre activité', subtitle: 'Pour organiser votre portefeuille de dossiers.',
        fields: [
          { key: 'nb_clients', label: 'Nombre de clients suivis', type: 'select', options: ['< 20', '20 à 50', '50 à 150', '> 150'] },
          { key: 'contentieux_an', label: 'Dossiers de contentieux par an', type: 'select', options: ['< 5', '5 à 20', '20 à 50', '> 50'] },
          { key: 'specialites', label: 'Spécialités', type: 'multi', options: ['TVA', 'IS / IRPP', 'Contentieux fiscal', 'Prix de transfert', 'Contrôle fiscal', 'Fiscalité internationale'], full: true },
          { key: 'secteurs_clients', label: 'Secteurs de vos clients', type: 'multi', options: SECTEURS.slice(0, 8), full: true },
        ],
      },
    ],
  },
  {
    id: 'verificateur', label: 'Vérificateur', who: 'Je prépare des notifications', icon: UserCheck, to: '/administration/controle-qualite',
    parcours: ['Déposez votre projet de notification', 'Corrigez les vices de procédure signalés', "Renforcez les chefs mal motivés avant l'envoi"],
    sections: [
      {
        title: 'Votre affectation', subtitle: "L'accès aux espaces de l'administration est réservé aux agents habilités.",
        fields: [
          { key: 'matricule_agent', label: "Matricule d'agent", type: 'text', required: true },
          { key: 'grade', label: 'Grade', type: 'select', required: true, options: ['Contrôleur', 'Inspecteur', 'Inspecteur central', 'Inspecteur principal', 'Inspecteur en chef'] },
          { key: 'structure', label: 'Structure', type: 'select', required: true, options: ['Centre régional de contrôle des impôts', 'Direction des grandes entreprises', 'Unité du contrôle national et des enquêtes fiscales', 'Bureau de contrôle des impôts'] },
          { key: 'gouvernorat', label: 'Gouvernorat', type: 'select', required: true, options: GOUVERNORATS },
        ],
      },
      {
        title: 'Votre activité de contrôle', subtitle: 'Pour adapter les contrôles qualité à vos vérifications.',
        fields: [
          { key: 'types_verification', label: 'Types de vérification', type: 'multi', options: ['Vérification préliminaire', 'Vérification approfondie'], full: true },
          { key: 'secteurs', label: 'Secteurs contrôlés', type: 'multi', options: SECTEURS.slice(0, 8), full: true },
          { key: 'notifications_mois', label: 'Notifications préparées par mois', type: 'select', options: ['< 5', '5 à 15', '15 à 30', '> 30'] },
          { key: 'besoin', label: 'Votre besoin principal', type: 'select', options: ['Éviter les vices de procédure', 'Mieux motiver les chefs', 'Gagner du temps de rédaction', 'Trouver les bons articles'] },
        ],
      },
    ],
  },
  {
    id: 'contentieux', label: 'Chef(fe) du contentieux', who: 'Je pilote le stock de dossiers', icon: Landmark, to: '/administration',
    parcours: ["Traitez d'abord les dossiers prioritaires", 'Ouvrez un dossier : score de solidité et explication', 'Validez ou non la proposition de conciliation'],
    sections: [
      {
        title: 'Votre périmètre', subtitle: 'Le stock et le tableau de bord seront filtrés sur votre périmètre.',
        fields: [
          { key: 'structure', label: 'Structure', type: 'select', required: true, options: ['Unité du contentieux fiscal (centrale)', 'Direction régionale', 'Direction des grandes entreprises'] },
          { key: 'perimetre', label: 'Périmètre', type: 'select', required: true, options: ['National', 'Régional'] },
          { key: 'gouvernorats', label: 'Gouvernorats suivis', type: 'multi', options: GOUVERNORATS, full: true, showIf: (v) => v.perimetre === 'Régional' },
          { key: 'taille_stock', label: 'Taille approximative du stock', type: 'select', options: ['< 100 dossiers', '100 à 500', '500 à 2 000', '> 2 000'] },
          { key: 'agents', label: "Nombre d'agents dans l'équipe", type: 'number', placeholder: '8' },
        ],
      },
      {
        title: 'Vos objectifs', subtitle: 'JISER priorise les dossiers selon vos objectifs.',
        fields: [
          { key: 'objectifs', label: 'Objectifs prioritaires', type: 'multi', required: true, full: true,
            options: ['Accélérer le recouvrement', 'Réduire les annulations', 'Développer la conciliation', 'Réduire la durée des dossiers'] },
          { key: 'seuil_alerte', label: "Seuil d'alerte (montant en DT)", type: 'number', placeholder: '500000', help: 'Les dossiers au-dessus de ce montant vous sont signalés.' },
          { key: 'rapport', label: 'Rapport de pilotage', type: 'select', options: ['Hebdomadaire', 'Mensuel', 'Trimestriel'] },
        ],
      },
    ],
  },
  {
    id: 'admin', label: 'Administrateur', who: 'Je gère la plateforme', icon: Settings, to: '/plateforme',
    parcours: ['Gérez les utilisateurs et les rôles', 'Mettez à jour la base juridique', 'Contrôlez le journal des recommandations IA'],
    sections: [
      {
        title: 'Votre organisation', subtitle: 'Structure et périmètre d\'administration.',
        fields: [
          { key: 'structure', label: 'Structure', type: 'text', required: true, placeholder: 'DSI, Ministère des Finances', full: true },
          { key: 'perimetre', label: 'Périmètre', type: 'select', required: true, options: ['National', 'Régional', 'Pilote'] },
          { key: 'nb_utilisateurs', label: "Nombre d'utilisateurs prévus", type: 'select', options: ['< 50', '50 à 500', '500 à 5 000', '> 5 000'] },
        ],
      },
      {
        title: 'Sécurité et conformité', subtitle: 'Règles appliquées à tous les utilisateurs.',
        fields: [
          { key: 'otp_obligatoire', label: 'Vérification OTP obligatoire à chaque connexion', type: 'toggle', full: true },
          { key: 'duree_session', label: 'Durée maximale de session', type: 'select', options: ['1 heure', '4 heures', '8 heures'] },
          { key: 'retention_journal', label: 'Conservation du journal IA', type: 'select', options: ['1 an', '5 ans', '10 ans'] },
          { key: 'revue_modele', label: 'Revue du modèle', type: 'select', options: ['Mensuelle', 'Trimestrielle', 'À chaque loi de finances'] },
        ],
      },
    ],
  },
]

export const roleConfig = (id: Role | null) => ROLES.find((r) => r.id === id) ?? null

export function validateSection(section: Section, values: Record<string, unknown>): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const f of section.fields) {
    if (f.showIf && !f.showIf(values)) continue
    const v = values[f.key]
    const empty = v === undefined || v === '' || (Array.isArray(v) && v.length === 0)
    if (f.required && empty) errors[f.key] = 'Champ obligatoire'
    else if (!empty && f.pattern && !f.pattern.test(String(v).toUpperCase().replace(/\s/g, ''))) errors[f.key] = f.patternMessage ?? 'Format invalide'
  }
  return errors
}
