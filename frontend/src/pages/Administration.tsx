import { BarChart3, Bot, FileCheck2, FolderKanban, Handshake } from 'lucide-react'
import { Navigate, Route, Routes } from 'react-router-dom'
import type { Session } from '../api'
import AppShell, { type NavItem } from '../components/AppShell'
import AssistantChat from '../components/AssistantChat'
import Conciliations from './administration/Conciliations'
import Controle from './administration/Controle'
import Dashboard from './administration/Dashboard'
import DossierPage from './administration/DossierPage'
import Stock from './administration/Stock'

const NAV: NavItem[] = [
  { to: '/administration', label: 'Tableau de bord', icon: BarChart3, end: true, ai: true },
  { to: '/administration/dossiers', label: 'Stock de dossiers', icon: FolderKanban },
  { to: '/administration/conciliations', label: 'Conciliations', icon: Handshake, ai: true },
  { to: '/administration/controle-qualite', label: 'Contrôle qualité', icon: FileCheck2, ai: true },
  { to: '/administration/copilote', label: 'Copilote juridique', icon: Bot, ai: true },
]

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
  return (
    <AppShell session={session} espace="Administration fiscale" nav={NAV}>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="dossiers" element={<Stock />} />
        <Route path="dossier/:id" element={<DossierPage />} />
        <Route path="conciliations" element={<Conciliations />} />
        <Route path="controle-qualite" element={<Controle />} />
        <Route path="copilote" element={<Copilote />} />
        <Route path="tableau-de-bord" element={<Navigate to="/administration" replace />} />
      </Routes>
    </AppShell>
  )
}
