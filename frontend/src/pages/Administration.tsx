import { BarChart3, Bot, FileCheck2, FolderKanban, Globe2, Handshake, MessagesSquare, Star, Users } from 'lucide-react'
import { Navigate, Route, Routes } from 'react-router-dom'
import type { Session } from '../api'
import AppShell, { type NavItem } from '../components/AppShell'
import AssistantChat from '../components/AssistantChat'
import Messagerie from '../components/Messagerie'
import FavorisPage from './FavorisPage'
import Conciliations from './administration/Conciliations'
import Controle from './administration/Controle'
import Dashboard from './administration/Dashboard'
import DossierPage from './administration/DossierPage'
import Equipe from './administration/Equipe'
import Pilotage from './administration/Pilotage'
import Stock from './administration/Stock'

const AGENT: NavItem[] = [
  { to: '/administration', label: 'Tableau de bord', icon: BarChart3, end: true, ai: true },
  { to: '/administration/dossiers', label: 'Stock de dossiers', icon: FolderKanban },
  { to: '/administration/messagerie', label: 'Messagerie', icon: MessagesSquare },
  { to: '/administration/conciliations', label: 'Conciliations', icon: Handshake, ai: true },
  { to: '/administration/controle-qualite', label: 'Contrôle qualité', icon: FileCheck2, ai: true },
  { to: '/administration/copilote', label: 'Copilote juridique', icon: Bot, ai: true },
  { to: '/administration/favoris', label: 'Favoris', icon: Star },
]
// each level of the hierarchy has its own menu (the API enforces the same rights)
const NAV: Record<string, NavItem[]> = {
  ministre: [
    { to: '/administration', label: 'Pilotage national', icon: Globe2, end: true },
    { to: '/administration/copilote', label: 'Copilote juridique', icon: Bot, ai: true },
    { to: '/administration/favoris', label: 'Favoris', icon: Star },
  ],
  chef_centre: [AGENT[0], AGENT[1], { to: '/administration/equipe', label: 'Équipe et validations', icon: Users }, ...AGENT.slice(2)],
  contentieux: AGENT,
}
const ESPACE: Record<string, string> = { ministre: 'Cabinet du ministre', chef_centre: 'Direction du centre', contentieux: 'Administration fiscale' }

function Copilote() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-navy-900">Copilote juridique</h1>
        <p className="mt-1 text-slate-500">Posez vos questions de procédure : l'IA répond à partir du CDPF, du Code de la TVA et du Code de l'IRPP/IS, et cite ses articles.</p>
      </div>
      <AssistantChat langue="fr" />
    </div>
  )
}

export default function Administration({ session }: { session: Session }) {
  const role = session.role ?? 'contentieux'
  const ministre = role === 'ministre'
  return (
    <AppShell session={session} espace={ESPACE[role] ?? 'Administration fiscale'} nav={NAV[role] ?? AGENT}>
      <Routes>
        <Route index element={ministre ? <Pilotage /> : <Dashboard />} />
        <Route path="copilote" element={<Copilote />} />
        <Route path="favoris" element={<FavorisPage />} />
        {!ministre && <>
          <Route path="dossiers" element={<Stock />} />
          <Route path="dossier/:id" element={<DossierPage />} />
          <Route path="messagerie" element={<Messagerie espace="administration" base="/administration/messagerie" />} />
          <Route path="messagerie/:id" element={<Messagerie espace="administration" base="/administration/messagerie" />} />
          <Route path="conciliations" element={<Conciliations />} />
          <Route path="controle-qualite" element={<Controle />} />
        </>}
        {role === 'chef_centre' && <Route path="equipe" element={<Equipe />} />}
        <Route path="*" element={<Navigate to="/administration" replace />} />
      </Routes>
    </AppShell>
  )
}
