import { Bot, FileText, FileUp, FolderOpen, LayoutDashboard, MessagesSquare, ShieldCheck, Star } from 'lucide-react'
import { Route, Routes } from 'react-router-dom'
import type { Session } from '../api'
import AppShell, { type NavItem } from '../components/AppShell'
import Messagerie from '../components/Messagerie'
import FavorisPage from './FavorisPage'
import Confidentialite from './entreprise/Confidentialite'
import { Analyser, Assistant, DossierDetail, EntrepriseDashboard, MesDossiers, MesReponses } from './entreprise/Pages'

const NAV: NavItem[] = [
  { to: '/entreprise', label: 'Tableau de bord', icon: LayoutDashboard, end: true },
  { to: '/entreprise/analyser', label: 'Analyser une notification', icon: FileUp, ai: true },
  { to: '/entreprise/dossiers', label: 'Mes dossiers', icon: FolderOpen },
  { to: '/entreprise/messagerie', label: 'Messagerie', icon: MessagesSquare },
  { to: '/entreprise/assistant', label: 'Assistant fiscal', icon: Bot, ai: true },
  { to: '/entreprise/reponses', label: 'Mes réponses', icon: FileText },
  { to: '/entreprise/favoris', label: 'Favoris', icon: Star },
  { to: '/entreprise/confidentialite', label: 'Confidentialité', icon: ShieldCheck },
]

export default function Entreprise({ session }: { session: Session }) {
  return (
    <AppShell session={session} espace="Espace entreprise" nav={NAV}>
      <Routes>
        <Route index element={<EntrepriseDashboard session={session} />} />
        <Route path="analyser" element={<Analyser session={session} />} />
        <Route path="dossiers" element={<MesDossiers />} />
        <Route path="dossiers/:id" element={<DossierDetail />} />
        <Route path="messagerie" element={<Messagerie espace="entreprise" base="/entreprise/messagerie" />} />
        <Route path="messagerie/:id" element={<Messagerie espace="entreprise" base="/entreprise/messagerie" />} />
        <Route path="assistant" element={<Assistant session={session} />} />
        <Route path="reponses" element={<MesReponses />} />
        <Route path="favoris" element={<FavorisPage />} />
        <Route path="confidentialite" element={<Confidentialite />} />
      </Routes>
    </AppShell>
  )
}
