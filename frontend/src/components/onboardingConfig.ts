import { Building2, Crown, Landmark, Scale, UserCog, type LucideIcon } from 'lucide-react'

// The platform administrator is not self-service: that account is reached only through its private link.
export type Role = 'entreprise' | 'ministre' | 'chef_centre' | 'contentieux'
export type Famille = 'entreprise' | 'administration'

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

export interface PieceConfig { type: string; label: string; help: string }

export interface RoleConfig {
  id: Role
  famille: Famille
  label: string
  who: string
  niveau?: string
  droits?: string[]
  icon: LucideIcon
  to: string
  sections: Section[]
  pieces: PieceConfig[]
  validateur: string
  parcours: string[]
}

export const FAMILLES: { id: Famille; label: string; who: string; icon: LucideIcon }[] = [
  { id: 'entreprise', label: 'Entreprise', who: "J'ai reçu une notification de redressement", icon: Building2 },
  { id: 'administration', label: 'Administration fiscale', who: 'Ministère des Finances, DGI ou centre régional', icon: Landmark },
]

export const GOUVERNORATS = ['Tunis', 'Ariana', 'Ben Arous', 'Manouba', 'Nabeul', 'Zaghouan', 'Bizerte', 'Béja', 'Jendouba', 'Le Kef',
  'Siliana', 'Sousse', 'Monastir', 'Mahdia', 'Sfax', 'Kairouan', 'Kasserine', 'Sidi Bouzid', 'Gabès', 'Médenine', 'Tataouine',
  'Gafsa', 'Tozeur', 'Kébili']
// 27 centres régionaux de contrôle des impôts (ministère des Finances): 16 of category A, 11 of category B
export const CENTRES = ['Tunis 1', 'Tunis 2', 'Tunis 3', 'Ariana', 'Ben Arous', 'Manouba', 'Bizerte', 'Nabeul', 'Sousse', 'Monastir',
  'Sfax 1', 'Sfax 2', 'Kairouan', 'Médenine', 'Mahdia', 'Gabès', 'Gafsa', 'Le Kef', 'Béja', 'Jendouba', 'Kasserine', 'Sidi Bouzid',
  'Zaghouan', 'Siliana', 'Kébili', 'Tozeur', 'Tataouine']
const SECTEURS = ['Commerce de gros', 'Commerce de détail', 'BTP', 'Industrie textile', 'Agroalimentaire', 'Services informatiques',
  'Transport et logistique', 'Promotion immobilière', 'Tourisme et hôtellerie', 'Professions libérales', 'Autre']
const IMPOTS = ['TVA', 'Impôt sur les sociétés', 'IRPP', 'Retenue à la source', "Droits d'enregistrement"]

export const MATRICULE_RE = /^\d{7}[A-Z]\/[A-Z]\/[A-Z]\/\d{3}$/
const MATRICULE_AGENT = { pattern: /^\d{4,10}$/, patternMessage: 'Identifiant unique (4 à 10 chiffres)' }

export const ROLES: RoleConfig[] = [
  {
    id: 'entreprise', famille: 'entreprise', label: "Chef d'entreprise", who: "J'ai reçu une notification de redressement", icon: Building2, to: '/entreprise',
    validateur: "l'administrateur de la plateforme",
    parcours: ['Déposez votre notification (PDF ou photo)', "Lisez ce qu'on vous reproche, chef par chef, en clair", 'Échangez avec l\'administration et répondez avant la date limite'],
    pieces: [
      { type: 'rne', label: 'Extrait du registre national des entreprises (RNE)', help: 'Moins de 3 mois. Il prouve que vous représentez la société.' },
      { type: 'cin', label: "Carte d'identité du gérant", help: 'Recto verso, ou passeport.' },
    ],
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
            help: 'Vous avez 45 jours à compter de cette date pour répondre (art. 44 CDPF, édition 2024).',
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
    id: 'ministre', famille: 'administration', label: 'Ministre des Finances', niveau: 'Niveau national · stratégique', icon: Crown, to: '/administration',
    who: 'Pilotage national du contentieux fiscal',
    droits: ['Tableau de bord national en temps réel, avec filtres', 'Statistiques anonymes uniquement (secret fiscal)', 'Simulateur d\'impact et chiffres officiels'],
    validateur: "l'administrateur de la plateforme, sur décret de nomination",
    parcours: ['Filtrez le stock national par gouvernorat, motif ou montant', 'Suivez l\'activité en temps réel', 'Mesurez l\'impact des mesures avec le simulateur'],
    pieces: [{ type: 'nomination', label: 'Décret de nomination', help: 'Ou attestation du cabinet.' }],
    sections: [
      {
        title: 'Votre cabinet', subtitle: 'Le tableau de bord national présente des statistiques anonymes : aucun nom de contribuable.',
        fields: [
          { key: 'cabinet', label: 'Cabinet', type: 'text', required: true, placeholder: 'Cabinet du ministre des Finances', full: true },
          { key: 'priorites', label: 'Priorités de pilotage', type: 'multi', full: true,
            options: ['Réduire le stock de dossiers', 'Accélérer le recouvrement', 'Développer la conciliation', 'Réduire les annulations', 'Équité entre régions'] },
          { key: 'rapport', label: 'Rapport de synthèse', type: 'select', options: ['Hebdomadaire', 'Mensuel', 'Trimestriel'] },
        ],
      },
    ],
  },
  {
    id: 'chef_centre', famille: 'administration', label: 'Chef de centre régional', niveau: 'Niveau régional · pilotage', icon: UserCog, to: '/administration',
    who: 'Je dirige un centre régional de contrôle des impôts (CRCI)',
    droits: ['Stock et tableau de bord de votre centre', 'Affectation des dossiers aux agents', 'Validation des conciliations importantes et des comptes agents'],
    validateur: "l'administrateur de la plateforme, sur décision de nomination",
    parcours: ['Affectez les dossiers prioritaires à vos agents', 'Validez les conciliations au-dessus du seuil', 'Suivez la charge de votre équipe'],
    pieces: [{ type: 'nomination', label: 'Décision de nomination', help: 'Ou attestation de fonction signée par la DGI.' }],
    sections: [
      {
        title: 'Votre centre', subtitle: 'Vous ne verrez que les dossiers de votre centre.',
        fields: [
          { key: 'centre', label: 'Centre régional de contrôle des impôts', type: 'select', required: true, options: CENTRES, full: true },
          { key: 'matricule_agent', label: 'Identifiant unique (matricule)', type: 'text', required: true, placeholder: '104587', ...MATRICULE_AGENT },
          { key: 'agents', label: "Nombre d'agents du contentieux", type: 'number', placeholder: '8' },
          { key: 'seuil_alerte', label: "Seuil d'alerte (montant en DT)", type: 'number', placeholder: '500000', help: 'Les dossiers au-dessus de ce montant vous sont signalés.' },
        ],
      },
    ],
  },
  {
    id: 'contentieux', famille: 'administration', label: 'Chargé(e) du contentieux', niveau: 'Niveau opérationnel', icon: Scale, to: '/administration',
    who: 'Je traite les dossiers de redressement de mon centre',
    droits: ['Dossiers de votre centre, affectés par votre chef', 'Avis juridique IA, contrôle qualité, copilote', 'Messagerie sécurisée avec les entreprises'],
    validateur: 'le chef de votre centre',
    parcours: ['Traitez d\'abord les dossiers qui vous sont affectés', 'Échangez avec l\'entreprise dans la messagerie sécurisée', 'Proposez une conciliation (validée par votre chef au-delà du seuil)'],
    pieces: [{ type: 'carte_pro', label: 'Carte professionnelle ou attestation de fonction', help: 'Délivrée par votre direction.' }],
    sections: [
      {
        title: 'Votre poste', subtitle: 'Votre compte sera validé par le chef de votre centre.',
        fields: [
          { key: 'centre', label: 'Centre régional de contrôle des impôts', type: 'select', required: true, options: CENTRES, full: true },
          { key: 'matricule_agent', label: 'Identifiant unique (matricule)', type: 'text', required: true, placeholder: '208761', ...MATRICULE_AGENT },
          { key: 'grade', label: 'Grade', type: 'select', required: true, options: ['Contrôleur des impôts', 'Inspecteur', 'Inspecteur central', 'Inspecteur en chef'] },
          { key: 'specialites', label: 'Spécialités', type: 'multi', full: true, options: ['TVA', 'Impôt sur les sociétés', 'IRPP', 'Prix de transfert', 'Retenues à la source'] },
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
