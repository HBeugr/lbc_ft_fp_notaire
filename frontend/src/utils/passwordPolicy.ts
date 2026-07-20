/**
 * Miroir exact de `app/core/password_policy.py`.
 *
 * Le backend rejette un mot de passe non conforme par un 422 Pydantic, dont le
 * `detail` est une liste d'erreurs et non un message affichable. Valider ici
 * avec les mêmes règles évite d'envoyer une requête vouée à l'échec et permet
 * d'afficher le motif réel à côté du champ.
 */
export const PASSWORD_MIN_LENGTH = 12

export const PASSWORD_HINT =
  '12 caractères minimum, avec au moins une majuscule, une minuscule, un chiffre et un caractère spécial.'

/** Retourne le motif de rejet, ou `null` si le mot de passe est conforme. */
export function checkPasswordStrength(v: string): string | null {
  if (v.length < PASSWORD_MIN_LENGTH) {
    return `Le mot de passe doit contenir au moins ${PASSWORD_MIN_LENGTH} caractères.`
  }
  if (!/[A-Z]/.test(v)) return 'Le mot de passe doit contenir au moins une majuscule.'
  if (!/[a-z]/.test(v)) return 'Le mot de passe doit contenir au moins une minuscule.'
  if (!/[0-9]/.test(v)) return 'Le mot de passe doit contenir au moins un chiffre.'
  if (!/[^a-zA-Z0-9]/.test(v)) return 'Le mot de passe doit contenir au moins un caractère spécial.'
  return null
}
