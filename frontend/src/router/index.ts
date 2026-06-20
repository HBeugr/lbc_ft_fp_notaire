import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ── Public auth routes ──────────────────────────────────────────
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/2fa/setup',
      name: '2fa-setup',
      component: () => import('@/views/auth/Setup2FAView.vue'),
      meta: { public: true },
    },
    {
      path: '/2fa/verify',
      name: '2fa-verify',
      component: () => import('@/views/auth/Verify2FAView.vue'),
      meta: { public: true },
    },
    {
      path: '/auth/change-password',
      name: 'change-password',
      component: () => import('@/views/auth/ChangePasswordView.vue'),
      meta: { requiresAuth: true, allowMustChange: true },
    },

    // ── Protected app routes (AppLayout) ────────────────────────────
    {
      path: '/',
      component: () => import('@/views/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/dashboard/DashboardView.vue'),
        },
        {
          path: 'kyc',
          name: 'kyc-list',
          component: () => import('@/views/kyc/KycListView.vue'),
        },
        {
          path: 'kyc/nouveau',
          name: 'kyc-new',
          component: () => import('@/views/kyc/KycNewDossierView.vue'),
        },
        {
          path: 'kyc/:id',
          name: 'kyc-detail',
          component: () => import('@/views/kyc/KycDetailView.vue'),
        },
        {
          path: 'kyc/:id/modifier',
          name: 'kyc-edit',
          component: () => import('@/views/kyc/KycEditView.vue'),
        },
        // Notaire-specific: KYC PP form (detailed notaire KYC)
        {
          path: 'dossiers/:id/kyc/pp',
          name: 'kyc-pp',
          component: () => import('@/views/kyc/KycPPView.vue'),
        },
        // Notaire-specific: KYC PM form (detailed notaire KYC)
        {
          path: 'dossiers/:id/kyc/pm',
          name: 'kyc-pm',
          component: () => import('@/views/kyc/KycPMView.vue'),
        },
        {
          path: 'risque',
          name: 'risk-matrix',
          component: () => import('@/views/risk/RiskMatrixView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'alertes',
          name: 'alertes',
          component: () => import('@/views/alertes/AlertesView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'dos',
          name: 'dos',
          component: () => import('@/views/dos/DosListView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        // Notaire-specific: DOS detail form
        {
          path: 'dos/:id',
          name: 'dos-detail',
          component: () => import('@/views/dos/DosFormView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'sanctions',
          name: 'sanctions',
          component: () => import('@/views/sanctions/SanctionsView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'registres',
          name: 'registres',
          component: () => import('@/views/registres/RegistresView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'audit',
          name: 'audit-log',
          component: () => import('@/views/audit/AuditLogView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'utilisateurs',
          name: 'users',
          component: () => import('@/views/users/UsersView.vue'),
          meta: { roles: ['admin', 'responsable_conformite'] },
        },
        {
          path: 'parametres',
          name: 'settings',
          component: () => import('@/views/settings/SettingsView.vue'),
          meta: { roles: ['admin', 'notaire_principal'] },
        },
        {
          path: 'revisions',
          name: 'revisions',
          component: () => import('@/views/revisions/RevisionsView.vue'),
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
        },
        {
          path: 'rapports',
          name: 'rapports',
          component: () => import('@/views/rapports/RapportsView.vue'),
          meta: { roles: ['admin', 'responsable_conformite'] },
        },
        {
          path: 'signalement-alerte',
          name: 'signalement-alerte',
          component: () => import('@/views/alertes/SignalementAlerteView.vue'),
          meta: { roles: ['admin', 'clercs'] },
        },
        {
          path: 'procedures',
          name: 'procedures',
          component: () => import('@/views/procedures/ProceduresView.vue'),
        },
        {
          path: 'mon-compte',
          name: 'mon-compte',
          component: () => import('@/views/account/MonCompteView.vue'),
        },
      ],
    },

    // ── Fallback ────────────────────────────────────────────────────
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  await auth.bootstrapReady

  // Redirect authenticated users away from login
  if (to.name === 'login' && auth.isAuthenticated) {
    if (auth.mustChangePassword) return { name: 'change-password' }
    return { name: 'dashboard' }
  }

  // Require authentication
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login' }
  }

  // Force password change — redirect to change-password for any protected route
  if (auth.isAuthenticated && auth.mustChangePassword && !to.meta.allowMustChange) {
    return { name: 'change-password' }
  }

  // Enforce role-based access
  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && auth.user && !allowedRoles.includes(auth.user.role)) {
    return { name: 'dashboard' }
  }
})

export default router
