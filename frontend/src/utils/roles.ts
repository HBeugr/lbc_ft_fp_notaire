export const ROLE_LABELS: Record<string, string> = {
  admin:                  'Administrateur',
  notaire_principal:      'Notaire Principal',
  responsable_conformite: 'Responsable Conformité',
  clercs:                 'Clerc Principal',
  declarant_centif:       'Déclarant CENTIF',
  autre_utilisateur:      'Autre utilisateur',
}

export function formatRole(role: string): string {
  return ROLE_LABELS[role] ?? role
}
