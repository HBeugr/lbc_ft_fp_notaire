import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Auth
    { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true } },
    { path: '/2fa/setup', name: '2fa-setup', component: () => import('@/views/auth/Setup2FAView.vue'), meta: { public: true } },
    { path: '/2fa/verify', name: '2fa-verify', component: () => import('@/views/auth/Verify2FAView.vue'), meta: { public: true } },

    // App (protected)
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },
    { path: '/dossiers', name: 'dossiers', component: () => import('@/views/dossiers/ListeView.vue') },
    { path: '/dossiers/:id', name: 'dossier-detail', component: () => import('@/views/dossiers/DetailView.vue') },
    { path: '/dossiers/:id/kyc/pp', name: 'kyc-pp', component: () => import('@/views/kyc/KycPPView.vue') },
    { path: '/dossiers/:id/kyc/pm', name: 'kyc-pm', component: () => import('@/views/kyc/KycPMView.vue') },
    { path: '/alertes', name: 'alertes', component: () => import('@/views/alertes/AlertesView.vue') },
    { path: '/dos', name: 'dos', component: () => import('@/views/dos/DosListView.vue') },
    { path: '/dos/:id', name: 'dos-detail', component: () => import('@/views/dos/DosFormView.vue') },
    { path: '/registres', name: 'registres', component: () => import('@/views/registres/RegistresView.vue') },
    { path: '/revisions', name: 'revisions', component: () => import('@/views/revisions/RevisionsView.vue') },
    { path: '/rapports', name: 'rapports', component: () => import('@/views/rapports/RapportsView.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/views/admin/AdminView.vue') },

    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.bootstrapReady

  if (to.meta.public) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

export default router
