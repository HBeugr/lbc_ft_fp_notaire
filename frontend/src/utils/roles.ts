export const ROLE_LABELS: Record<string, string> = {
  admin:                  'Administrateur',
  notaire_principal:      'Notaire Principal',
  responsable_conformite: 'Responsable Conformité',
  clercs:                 'Clerc Principal',
}

export function formatRole(role: string): string {
  return ROLE_LABELS[role] ?? role
}
