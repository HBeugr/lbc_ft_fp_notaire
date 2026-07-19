import { ref, onBeforeUnmount } from 'vue'

/**
 * URL d'objet à durée de vie maîtrisée.
 *
 * Les endpoints d'image de la plateforme exigent l'en-tête `Authorization` :
 * l'image est récupérée en blob puis affichée via `URL.createObjectURL`. Chaque
 * URL créée doit être révoquée — au remplacement comme au démontage du composant
 * — sans quoi le blob reste en mémoire jusqu'au rechargement de l'onglet.
 */
export function useObjectUrl() {
  const url = ref<string | null>(null)

  /** Remplace la source affichée. `null` libère l'URL courante sans en créer. */
  function set(source: Blob | null) {
    if (url.value) URL.revokeObjectURL(url.value)
    url.value = source ? URL.createObjectURL(source) : null
  }

  onBeforeUnmount(() => {
    if (url.value) URL.revokeObjectURL(url.value)
  })

  return { url, set }
}
