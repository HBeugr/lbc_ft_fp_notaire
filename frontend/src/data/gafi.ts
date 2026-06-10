// Référentiel GAFI/FATF — listes au 13/02/2026 (mise à jour biannuelle FATF)
// Miroir de backend/app/core/gafi.py

export const LISTE_NOIRE_GAFI: string[] = [
  'Corée du Nord', 'North Korea', 'DPRK',
  'Iran', "République islamique d'Iran",
  'Myanmar', 'Birmanie',
]

export const LISTE_GRISE_GAFI: string[] = [
  'Algérie', 'Angola', 'Bolivie', 'Bulgarie', 'Burkina Faso', 'Cameroun',
  "Côte d'Ivoire", 'République démocratique du Congo', 'RDC',
  'Haïti', 'Kenya', 'Koweït', 'Laos',
  'Liban', 'Monaco', 'Namibie', 'Népal',
  'Papouasie-Nouvelle-Guinée', 'Soudan du Sud',
  'Syrie', 'Venezuela', 'Vietnam',
  'Îles Vierges britanniques', 'Yémen',
]

function norm(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

const noireSet = new Set(LISTE_NOIRE_GAFI.map(norm))
const griseSet = new Set(LISTE_GRISE_GAFI.map(norm))

export function getStatutGafi(pays: string): 'liste_noire' | 'liste_grise' | 'ok' {
  if (!pays) return 'ok'
  const n = norm(pays)
  if (noireSet.has(n)) return 'liste_noire'
  if (griseSet.has(n)) return 'liste_grise'
  return 'ok'
}
