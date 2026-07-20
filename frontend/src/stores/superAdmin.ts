import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SuperAdminOut } from '@/services/superAdmin'

/**
 * Session de la console d'exploitation.
 *
 * Population totalement distincte des utilisateurs de cabinet : le jeton est
 * conservé sous une clé propre (`super-admin`) et n'est jamais posé sur
 * `axios.defaults`, pour qu'une session Super-Admin et une session cabinet
 * puissent coexister dans le même navigateur sans s'écraser.
 */
export const useSuperAdminStore = defineStore('super-admin', () => {
  // Purge des jetons écrits par les versions antérieures, qui persistaient dans
  // `localStorage` : sans ce nettoyage un jeton d'exploitation survivrait
  // indéfiniment sur le poste, ce que le passage à `sessionStorage` vise à éviter.
  try {
    localStorage.removeItem('super-admin')
  } catch {
    // Stockage indisponible (mode privé) — rien à purger.
  }

  const accessToken = ref<string | null>(null)
  const superAdmin = ref<SuperAdminOut | null>(null)
  const isAuthenticated = computed(() => !!accessToken.value && !!superAdmin.value)
  const mustChangePassword = computed(() => !!superAdmin.value?.must_change_password)
  const fullName = computed(() =>
    superAdmin.value ? `${superAdmin.value.first_name} ${superAdmin.value.last_name}` : ''
  )

  function setSession(token: string, admin: SuperAdminOut) {
    accessToken.value = token
    superAdmin.value = admin
  }

  function setSuperAdmin(admin: SuperAdminOut) {
    superAdmin.value = admin
  }

  function clearSession() {
    accessToken.value = null
    superAdmin.value = null
    try {
      sessionStorage.removeItem('super-admin')
    } catch {
      // Stockage indisponible — rien à purger.
    }
  }

  return {
    accessToken,
    superAdmin,
    isAuthenticated,
    mustChangePassword,
    fullName,
    setSession,
    setSuperAdmin,
    clearSession,
  }
  // Le jeton est persisté pour survivre à un rechargement : la console n'a pas
  // de cookie de refresh, contrairement à l'espace cabinet. On le range dans
  // `sessionStorage` et non `localStorage` : la console d'exploitation est un
  // outil d'administration, la session doit expirer à la fermeture de l'onglet
  // et le jeton reste ainsi hors de portée des autres onglets (surface XSS réduite).
}, { persist: { key: 'super-admin', storage: sessionStorage, paths: ['accessToken', 'superAdmin'] } })
