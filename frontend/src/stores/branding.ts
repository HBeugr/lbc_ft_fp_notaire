import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tenantService } from '@/services/tenant'

/**
 * Logo du cabinet courant.
 *
 * L'endpoint `GET /api/tenant/logo` exige l'en-tête `Authorization` : une balise
 * `<img src="/api/tenant/logo">` ne l'enverrait pas et afficherait une image
 * cassée. L'image est donc récupérée en blob par l'instance axios, puis exposée
 * sous forme d'URL d'objet.
 *
 * L'URL est partagée par toutes les vues (barre latérale, page Paramètres) afin
 * qu'un changement de logo soit répercuté partout, et révoquée à chaque
 * remplacement pour ne pas fuir de mémoire.
 */
export const useBrandingStore = defineStore('branding', () => {
  /** URL d'objet du logo, ou `null` quand le cabinet n'en a pas. */
  const logoUrl = ref<string | null>(null)

  /** Horodatage du logo actuellement affiché — évite de retélécharger à l'identique. */
  const versionAffichee = ref<string | null>(null)

  /** Horodatage en cours de téléchargement — évite les requêtes concurrentes en double. */
  let versionEnCours: string | null = null

  function revoquer() {
    if (logoUrl.value) {
      URL.revokeObjectURL(logoUrl.value)
      logoUrl.value = null
    }
  }

  /**
   * Charge le logo correspondant à l'horodatage donné.
   *
   * `version` à `null` / `undefined` signifie « aucun logo » : on ne lance
   * AUCUNE requête, ce qui évite un 404 systématique dans la console du
   * navigateur pour les cabinets sans logo.
   */
  async function charger(version: string | null | undefined) {
    if (!version) {
      revoquer()
      versionAffichee.value = null
      return
    }
    if (version === versionAffichee.value && logoUrl.value) return
    if (version === versionEnCours) return

    versionEnCours = version
    try {
      const blob = await tenantService.logoBlob(version)
      revoquer()
      logoUrl.value = URL.createObjectURL(blob)
      versionAffichee.value = version
    } catch {
      // 404 ou stockage indisponible : l'interface retombe sur l'icône générique.
      revoquer()
      versionAffichee.value = null
    } finally {
      if (versionEnCours === version) versionEnCours = null
    }
  }

  /** Purge l'URL d'objet — déconnexion, changement de cabinet. */
  function reinitialiser() {
    revoquer()
    versionAffichee.value = null
    versionEnCours = null
  }

  return { logoUrl, charger, reinitialiser }
})
