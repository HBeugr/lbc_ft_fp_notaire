import { test, expect, APIRequestContext } from '@playwright/test'

/**
 * Vérifie la chaîne d'assignation notaire via l'API (aucun navigateur requis).
 * Pour chaque rôle : login → GET /dossiers/assignables → on contrôle que
 *   1. AUCUN rôle hors-chaîne n'est exposé (invariant de sécurité) ;
 *   2. la cible d'escalade attendue est bien présente ;
 *   3. l'auto-assignation (présence de soi-même) est conforme au rôle.
 *
 * Miroir du backend app/routers/dossiers.py (_CHAIN_NEXT / _SELF_ASSIGN_ROLES).
 */
const CHAIN_NEXT: Record<string, string[]> = {
  autre_utilisateur:      ['clercs', 'declarant_centif'],
  clercs:                 ['notaire_principal'],
  declarant_centif:       ['notaire_principal'],
  responsable_conformite: ['notaire_principal'],
  notaire_principal:      ['admin'],
  admin:                  ['autre_utilisateur', 'clercs', 'declarant_centif',
                           'responsable_conformite', 'notaire_principal', 'admin'],
}
const SELF_ASSIGN = new Set(['clercs', 'declarant_centif', 'responsable_conformite', 'admin'])

function allowedRoles(role: string): Set<string> {
  const set = new Set(CHAIN_NEXT[role] ?? [])
  if (SELF_ASSIGN.has(role)) set.add(role)
  return set
}

// (clé rôle, variables d'env, escalade attendue si un compte cible existe, optionnel)
const ROLES = [
  { role: 'admin',                  email: 'E2E_ADMIN_EMAIL',   pwd: 'E2E_ADMIN_PWD',   escalation: null,                optional: false },
  { role: 'notaire_principal',      email: 'E2E_NOTAIRE_EMAIL', pwd: 'E2E_NOTAIRE_PWD', escalation: 'admin',            optional: false },
  { role: 'responsable_conformite', email: 'E2E_RC_EMAIL',      pwd: 'E2E_RC_PWD',      escalation: 'notaire_principal', optional: false },
  { role: 'clercs',                 email: 'E2E_CLERC_EMAIL',   pwd: 'E2E_CLERC_PWD',   escalation: 'notaire_principal', optional: false },
  { role: 'declarant_centif',       email: 'E2E_DC_EMAIL',      pwd: 'E2E_DC_PWD',      escalation: 'notaire_principal', optional: true },
  { role: 'autre_utilisateur',      email: 'E2E_AUTRE_EMAIL',   pwd: 'E2E_AUTRE_PWD',   escalation: null,                optional: true },
]

async function login(request: APIRequestContext, email: string, password: string) {
  const res = await request.post('/api/auth/login', { data: { email, password } })
  expect(res.status(), `login ${email}`).toBe(200)
  const body = await res.json()
  expect(body.access_token, 'access_token présent').toBeTruthy()
  return { token: body.access_token as string, userId: body.user.id as string, role: body.user.role as string }
}

async function assignables(request: APIRequestContext, token: string) {
  const res = await request.get('/api/dossiers/assignables', {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(res.status(), 'GET /dossiers/assignables').toBe(200)
  return (await res.json()) as { id: string; full_name: string; role: string }[]
}

for (const cfg of ROLES) {
  const email = process.env[cfg.email]
  const password = process.env[cfg.pwd]

  test(`chaîne d'assignation — ${cfg.role}`, async ({ request }) => {
    test.skip(!email || !password, `Identifiants ${cfg.email}/${cfg.pwd} absents du .env.e2e`)

    const me = await login(request, email!, password!)
    expect(me.role, 'rôle du compte connecté').toBe(cfg.role)

    const list = await assignables(request, me.token)
    const rolesReturned = new Set(list.map((u) => u.role))
    const allowed = allowedRoles(cfg.role)

    // 1. Invariant de sécurité : aucun rôle hors-chaîne exposé.
    for (const r of rolesReturned) {
      expect(allowed.has(r), `rôle "${r}" ne doit PAS être assignable par ${cfg.role}`).toBeTruthy()
    }

    // 2. La cible d'escalade attendue est présente (un compte de ce rôle existe en dev).
    if (cfg.escalation) {
      expect(rolesReturned.has(cfg.escalation),
        `${cfg.role} doit pouvoir router vers ${cfg.escalation}`).toBeTruthy()
    }

    // 3. Auto-assignation : présence (ou absence) de soi-même conforme au rôle.
    const selfPresent = list.some((u) => u.id === me.userId)
    if (SELF_ASSIGN.has(cfg.role)) {
      expect(selfPresent, `${cfg.role} doit pouvoir s'auto-assigner (se voir dans la liste)`).toBeTruthy()
    } else {
      expect(selfPresent, `${cfg.role} ne doit PAS pouvoir s'auto-assigner`).toBeFalsy()
    }
  })
}
