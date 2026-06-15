import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

export interface NavItem {
  label: string
  icon: string      // SVG path data (24×24 viewBox)
  to: string        // route name
  badge?: string    // optional count badge
}

// SVG paths (stroke-based, 24×24)
const ICONS = {
  dashboard: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  signalement: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  audit: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
  kyc: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  risk: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  alerts: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
  dos: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  sanctions: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  registres: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
  users: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  settings: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
}

// Notaire roles: notaire_principal, responsable_conformite (RC), clercs (Clerc Principal),
// declarant_centif, autre_utilisateur, admin
type NotaireRole =
  | 'admin'
  | 'notaire_principal'
  | 'responsable_conformite'
  | 'clercs'
  | 'declarant_centif'
  | 'autre_utilisateur'

const ROLE_ACCESS: Record<string, NotaireRole[]> = {
  dashboard:          ['admin', 'notaire_principal', 'responsable_conformite', 'clercs', 'declarant_centif', 'autre_utilisateur'],
  kyc:                ['admin', 'notaire_principal', 'responsable_conformite', 'clercs', 'declarant_centif', 'autre_utilisateur'],
  signalement_alerte: ['admin', 'clercs'],
  risk:               ['admin', 'notaire_principal', 'responsable_conformite'],
  alerts:             ['admin', 'notaire_principal', 'responsable_conformite', 'declarant_centif'],
  dos:                ['admin', 'notaire_principal', 'responsable_conformite', 'declarant_centif'],
  sanctions:          ['admin', 'notaire_principal', 'responsable_conformite', 'declarant_centif'],
  registres:          ['admin', 'notaire_principal', 'responsable_conformite'],
  audit:              ['admin', 'notaire_principal', 'responsable_conformite'],
  users:              ['admin', 'responsable_conformite'],
  settings:           ['admin', 'notaire_principal'],
}

const ALL_NAV: NavItem[] = [
  { label: 'Tableau de bord',      icon: ICONS.dashboard,  to: 'dashboard' },
  { label: 'Dossiers KYC',         icon: ICONS.kyc,        to: 'kyc-list' },
  { label: 'Signalement alerte',   icon: ICONS.signalement, to: 'signalement-alerte' },
  { label: 'Matrice de risque',    icon: ICONS.risk,       to: 'risk-matrix' },
  { label: 'Alertes',              icon: ICONS.alerts,     to: 'alertes' },
  { label: 'Opérations Suspectes', icon: ICONS.dos,        to: 'dos' },
  { label: 'Screening sanctions',  icon: ICONS.sanctions,  to: 'sanctions' },
  { label: 'Registres légaux',     icon: ICONS.registres,  to: 'registres' },
  { label: 'Journal d\'audit',     icon: ICONS.audit,      to: 'audit-log' },
  { label: 'Utilisateurs',         icon: ICONS.users,      to: 'users' },
  { label: 'Paramètres',           icon: ICONS.settings,   to: 'settings' },
]

const KEY_MAP: Record<string, string> = {
  'dashboard':          'dashboard',
  'kyc-list':           'kyc',
  'risk-matrix':        'risk',
  'alertes':            'alerts',
  'dos':                'dos',
  'sanctions':          'sanctions',
  'registres':          'registres',
  'audit-log':          'audit',
  'signalement-alerte': 'signalement_alerte',
  'users':              'users',
  'settings':           'settings',
}

export function useNav() {
  const auth = useAuthStore()
  const notif = useNotificationsStore()

  const navItems = computed<NavItem[]>(() =>
    ALL_NAV.filter(item => {
      const key = KEY_MAP[item.to]
      const allowed = ROLE_ACCESS[key]
      return allowed && auth.user && (allowed as string[]).includes(auth.user.role)
    }).map(item => {
      if (!notif.hasPendingWeightsUpdate) return item
      const role = auth.user?.role
      if (item.to === 'settings' && role === 'notaire_principal') return { ...item, badge: '!' }
      if (item.to === 'risk-matrix' && role === 'responsable_conformite') return { ...item, badge: '!' }
      return item
    })
  )

  return { navItems }
}
