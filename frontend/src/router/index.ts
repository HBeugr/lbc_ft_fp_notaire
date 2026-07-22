import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSuperAdminStore } from '@/stores/superAdmin'

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

    // ── Cabinet non actif (suspendu / en configuration / archivé) ───
    {
      path: '/compte-suspendu',
      name: 'compte-suspendu',
      component: () => import('@/views/tenant/CompteSuspenduView.vue'),
      // allowMustChange : un cabinet bloqué doit voir l'explication plutôt qu'un
      // formulaire de changement de mot de passe que l'API refusera (402).
      meta: { allowInactiveTenant: true, allowMustChange: true },
    },

    // ── Console d'exploitation (Super-Admin plateforme) ─────────────
    {
      path: '/super-admin/login',
      name: 'super-admin-login',
      component: () => import('@/views/superadmin/SuperAdminLoginView.vue'),
      meta: { public: true, superAdminPublic: true },
    },
    {
      path: '/super-admin',
      component: () => import('@/views/superadmin/SuperAdminLayout.vue'),
      meta: { superAdmin: true },
      children: [
        {
          path: '',
          name: 'super-admin-dashboard',
          component: () => import('@/views/superadmin/SuperAdminDashboardView.vue'),
        },
        {
          path: 'cabinets',
          name: 'super-admin-tenants',
          component: () => import('@/views/superadmin/TenantsListView.vue'),
        },
        {
          path: 'cabinets/nouveau',
          name: 'super-admin-tenant-create',
          component: () => import('@/views/superadmin/TenantCreateView.vue'),
        },
        {
          path: 'cabinets/:id',
          name: 'super-admin-tenant-detail',
          component: () => import('@/views/superadmin/TenantDetailView.vue'),
        },
        {
          path: 'journal',
          name: 'super-admin-audit',
          component: () => import('@/views/superadmin/ExploitationAuditView.vue'),
        },
        {
          path: 'super-admins',
          name: 'super-admin-admins',
          component: () => import('@/views/superadmin/SuperAdminsView.vue'),
        },
        {
          path: 'compte',
          name: 'super-admin-account',
          component: () => import('@/views/superadmin/SuperAdminAccountView.vue'),
          // Seule route de la console accessible avec un mot de passe encore
          // à changer : c'est là qu'on le change.
          meta: { allowMustChange: true },
        },
      ],
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
          meta: { roles: ['admin', 'notaire_principal', 'responsable_conformite'] },
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

  // ── Console d'exploitation : session totalement indépendante du cabinet ──
  if (to.meta.superAdmin || to.meta.superAdminPublic) {
    const sa = useSuperAdminStore()

    if (to.meta.superAdminPublic) {
      return sa.isAuthenticated ? { name: 'super-admin-dashboard' } : true
    }

    if (!sa.isAuthenticated) {
      return { name: 'super-admin-login' }
    }

    // Mot de passe initial encore en place : la console est verrouillée sur la
    // page de compte tant qu'il n'est pas changé. Sans ce garde, la bannière
    // d'avertissement restait purement décorative et le mot de passe de seed
    // pouvait vivre indéfiniment.
    if (sa.mustChangePassword && !to.meta.allowMustChange) {
      return { name: 'super-admin-account' }
    }
    return true
  }

  await auth.bootstrapReady

  // Session en attente de validation 2FA : le jeton d'accès porte le claim
  // `totp_pending`. Tant que le code n'est pas saisi, la session n'est PAS
  // authentifiée — on la maintient sur la page de vérification. Sans ce garde, un
  // simple retour navigateur vers /login retombait sur la redirection « déjà
  // connecté » → dashboard, contournant le second facteur (Art. 29).
  if (auth.totpPending) {
    return to.name === '2fa-verify' ? true : { name: '2fa-verify' }
  }

  // Redirect authenticated users away from login
  if (to.name === 'login' && auth.isAuthenticated) {
    if (auth.mustChangePassword) return { name: 'change-password' }
    return { name: 'dashboard' }
  }

  // Cabinet non actif : seul `production` ouvre la plateforme. Contrôlé AVANT
  // l'authentification et le changement de mot de passe — un cabinet bloqué est
  // un arrêt plus fort, et l'API refuse de renouveler le jeton d'accès dans ce
  // cas : exiger d'abord un jeton renverrait l'utilisateur au formulaire de
  // connexion, sans jamais lui expliquer pourquoi son accès est fermé.
  if (auth.tenantBlocked && !to.meta.public && !to.meta.allowInactiveTenant) {
    return { name: 'compte-suspendu' }
  }

  // Require authentication — une session dont le cabinet est bloqué reste
  // recevable sur les routes marquées `allowInactiveTenant` (page d'explication).
  if (!to.meta.public && !auth.isAuthenticated && !auth.tenantBlocked) {
    return { name: 'login' }
  }

  // Cabinet redevenu actif : la page de blocage n'a plus lieu d'être.
  if (to.name === 'compte-suspendu' && auth.isAuthenticated && auth.tenantActive) {
    return { name: 'dashboard' }
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
