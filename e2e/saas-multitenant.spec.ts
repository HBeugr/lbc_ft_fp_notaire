import { test, expect, type Page, type BrowserContext, type Browser } from '@playwright/test'

/**
 * Validation navigateur de la migration SaaS multi-tenant.
 *
 * Couvre les écrans nouveaux ou modifiés par la migration :
 *   1. connexion cabinet et arrivée sur le tableau de bord ;
 *   2. branding par cabinet dans la barre latérale ;
 *   3. encart « Mon cabinet » de la page Paramètres ;
 *   4. console d'exploitation Super-Admin (liste des cabinets) ;
 *   5. création d'un cabinet + affichage unique du mot de passe temporaire ;
 *   6. étanchéité des sessions cabinet / console ;
 *   7. suspension d'un cabinet → bandeau + page de blocage → réactivation.
 *
 * Rejouable : le cabinet de test est créé à chaque exécution avec un slug et des
 * emails aléatoires. Le cabinet `demo` n'est jamais modifié.
 */

/**
 * La configuration racine impose `Content-Type: application/json` pour la suite
 * API (assignation.spec.ts). Appliqué à un contexte navigateur, cet en-tête
 * déclenche un préflight CORS sur les ressources tierces (polices) et pollue la
 * console. On le neutralise ici : ces tests pilotent un vrai navigateur.
 */
test.use({ extraHTTPHeaders: {} })

// ── Identifiants ─────────────────────────────────────────────────────────────
const NOTAIRE_EMAIL = process.env.E2E_NOTAIRE_EMAIL || 'notaire@notaire.local'
const NOTAIRE_PWD = process.env.E2E_NOTAIRE_PWD || 'Notaire2026!'
const SA_EMAIL = process.env.E2E_SUPERADMIN_EMAIL || 'superadmin@plateforme.local'
const SA_PWD = process.env.E2E_SUPERADMIN_PWD || 'SuperAdmin2026!'
const CLERC_EMAIL = process.env.E2E_CLERC_EMAIL || 'clerc@notaire.local'
const CLERC_PWD = process.env.E2E_CLERC_PWD || 'Clerc2026!'

/** Cabinet de démonstration seedé — lecture seule dans cette suite. */
const DEMO_NOM = 'Étude Notariale de Démonstration'
const DEMO_SLUG = 'demo'

// ── Collecte des erreurs JS ──────────────────────────────────────────────────

/**
 * Branche les écouteurs d'erreurs sur une page et retourne l'accumulateur.
 * Les erreurs réseau attendues (402/403 du portier de suspension) sont filtrées :
 * ce sont des réponses métier, pas des défauts de l'interface.
 */
function watchErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return
    const text = msg.text()
    // Bruit réseau attendu, journalisé par le navigateur et non par l'application :
    //  - statuts >= 400 (401 avant rafraîchissement du jeton, 402/403 du portier) ;
    //  - flux SSE des alertes coupé à chaque navigation (EventSource détruit).
    if (/Failed to load resource|status of (401|402|403)|ERR_INCOMPLETE_CHUNKED_ENCODING/i.test(text)) return
    errors.push(`console: ${text}`)
  })
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`))
  return errors
}

function expectNoErrors(errors: string[], parcours: string) {
  expect(errors, `erreurs JS pendant « ${parcours} »`).toEqual([])
}

// ── Helpers de connexion ─────────────────────────────────────────────────────

/**
 * Connexion d'un utilisateur de cabinet.
 * On attend d'avoir quitté `/login` : selon le compte, l'arrivée se fait sur le
 * tableau de bord ou sur l'écran de changement de mot de passe initial.
 */
async function loginCabinet(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.locator('#email').fill(email)
  await page.locator('#password').fill(password)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page).not.toHaveURL(/\/login$/)
}

/**
 * Navigation avec chargement complet de page, en attendant la fin du
 * rafraîchissement silencieux déclenché au démarrage de l'application.
 *
 * Indispensable dès qu'une autre navigation suit : le cookie `refresh_token` est
 * tourné à chaque appel de /api/auth/refresh. Naviguer pendant que la requête est
 * en vol ferait perdre au navigateur le nouveau cookie, alors que l'ancien vient
 * d'être révoqué côté serveur — la session suivante échouerait alors par
 * intermittence.
 */
async function gotoStable(page: Page, path: string) {
  const refresh = page
    .waitForResponse((r) => r.url().includes('/api/auth/refresh'), { timeout: 10_000 })
    .catch(() => null)
  await page.goto(path)
  await refresh
}

/** Connexion à la console d'exploitation jusqu'à la liste des cabinets. */
async function loginSuperAdmin(page: Page) {
  await page.goto('/super-admin/login')
  await page.locator('#sa-email').fill(SA_EMAIL)
  await page.locator('#sa-password').fill(SA_PWD)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await expect(page.getByRole('heading', { name: 'Cabinets notariaux' })).toBeVisible()
}

/**
 * Change le statut d'un cabinet depuis sa fiche de la console.
 * Les modales sont téléportées dans `body` : on les cible via `.modal-overlay`.
 */
async function setStatutDepuisConsole(
  page: Page,
  tenantId: string,
  action: 'Activer' | 'Suspendre',
  motif?: string,
) {
  await page.goto(`/super-admin/cabinets/${tenantId}`)
  await page.locator('.btn-success, .btn-ghost, .btn-danger').first().waitFor()
  await page.getByRole('button', { name: action, exact: true }).click()

  if (action === 'Suspendre') {
    const modal = page.locator('.modal-overlay')
    await expect(modal.getByRole('heading', { name: 'Suspendre ce cabinet ?' })).toBeVisible()
    if (motif) await modal.locator('textarea').fill(motif)
    await modal.getByRole('button', { name: 'Suspendre', exact: true }).click()
  }
}

// ── Cabinet créé, partagé entre les tests de la série ────────────────────────
const stamp = `${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`
const nouveauCabinet = {
  nom: `Étude E2E ${stamp}`,
  slug: `e2e-${stamp}`,
  // `.test` est un TLD réservé, refusé par la validation EmailStr du backend.
  contactEmail: `contact-${stamp}@e2e-notaire.ci`,
  adminEmail: `admin-${stamp}@e2e-notaire.ci`,
  adminPrenom: 'Awa',
  adminNom: 'Koffi',
  /** Renseignés au moment de la création. */
  id: '',
  tempPassword: '',
  /** Mot de passe défini par l'administrateur à sa première connexion. */
  nouveauPassword: 'CabinetE2E2026!',
}

// La configuration racine fixe `fullyParallel: false` : les tests d'un même
// fichier s'exécutent en série dans un seul worker, ce qui permet de transmettre
// le cabinet créé au test 5 jusqu'au test 7 via `nouveauCabinet`.

// ── 1. Connexion cabinet ─────────────────────────────────────────────────────
test('1 — connexion cabinet et arrivée sur le tableau de bord', async ({ page }) => {
  const errors = watchErrors(page)

  await loginCabinet(page, NOTAIRE_EMAIL, NOTAIRE_PWD)

  await expect(page).toHaveURL(/\/$/)
  await expect(page.locator('.sidebar')).toBeVisible()
  await expect(page.locator('.sidebar .user-name')).not.toBeEmpty()

  expectNoErrors(errors, 'connexion cabinet')
})

// ── 2. Branding par cabinet ──────────────────────────────────────────────────
test('2 — la barre latérale affiche le nom du cabinet, pas le libellé générique', async ({ page }) => {
  const errors = watchErrors(page)

  await loginCabinet(page, NOTAIRE_EMAIL, NOTAIRE_PWD)

  // `.logo-title` porte le branding ; `.logo-sub` reste la mention réglementaire.
  const titre = page.locator('.sidebar .logo-title')
  await expect(titre).toHaveText(DEMO_NOM)
  await expect(page.locator('.sidebar .logo-sub')).toHaveText(/CONFORMITÉ NOTARIALE/)

  // Le libellé générique d'avant la migration ne doit plus servir de titre.
  await expect(titre).not.toHaveText('LBC/FT/FP')

  // Le branding survit à un rechargement (réhydratation du store + /tenant/me).
  await page.reload()
  await expect(titre).toHaveText(DEMO_NOM)

  expectNoErrors(errors, 'branding cabinet')
})

// ── 3. Encart « Mon cabinet » ────────────────────────────────────────────────
test('3 — l’encart « Mon cabinet » de la page Paramètres est complet', async ({ page }) => {
  const errors = watchErrors(page)

  await loginCabinet(page, NOTAIRE_EMAIL, NOTAIRE_PWD)
  await page.goto('/parametres')

  const carte = page.locator('.card').filter({ has: page.getByRole('heading', { name: 'Mon cabinet' }) })
  await expect(carte).toBeVisible()

  /**
   * Valeur affichée en face d'un intitulé de l'encart.
   * Le locator passé à `has:` doit être construit depuis `page` : il est résolu
   * relativement à chaque `.info-row` candidate.
   */
  const valeur = (label: string) =>
    carte
      .locator('.info-row')
      .filter({ has: page.locator('.info-label', { hasText: label }) })
      .locator('.info-val')

  await expect(valeur('Nom du cabinet')).toHaveText(DEMO_NOM)
  await expect(valeur('Identifiant')).toHaveText(DEMO_SLUG)
  await expect(valeur('Pays')).toHaveText('CI')

  // N° agrément : valeur si renseignée, tiret cadratin sinon — jamais vide.
  await expect(valeur('N° agrément')).toHaveText(/\S/)

  // Quota de sièges : nombre, ou « Illimité » quand max_users vaut 0.
  await expect(valeur('Quota de sièges')).toHaveText(/^(\d+|Illimité)$/)

  // Statut du cabinet, badge en en-tête de carte.
  await expect(carte.locator('.badge-statut')).toHaveText('En production')

  expectNoErrors(errors, 'encart Mon cabinet')
})

// ── 4. Console Super-Admin ───────────────────────────────────────────────────
test('4 — la console Super-Admin liste les cabinets avec leur statut', async ({ page }) => {
  const errors = watchErrors(page)

  await loginSuperAdmin(page)

  await expect(page).toHaveURL(/\/super-admin$/)
  await expect(page.locator('.sidebar .logo-title')).toHaveText('EXPLOITATION')

  // Le cabinet de démonstration doit figurer dans la liste, avec un statut.
  const ligneDemo = page.locator('.tenants-table tbody tr').filter({ hasText: DEMO_NOM })
  await expect(ligneDemo).toHaveCount(1)
  await expect(ligneDemo.locator('.tenant-slug')).toHaveText(DEMO_SLUG)
  await expect(ligneDemo.locator('.badge')).toHaveText('En production')

  // Chaque ligne porte un badge de statut renseigné (invariant de la liste).
  const badges = page.locator('.tenants-table tbody tr .badge')
  expect(await badges.count()).toBeGreaterThan(0)
  for (const texte of await badges.allTextContents()) {
    expect(['En configuration', 'En production', 'Suspendu', 'Archivé']).toContain(texte.trim())
  }

  expectNoErrors(errors, 'console Super-Admin')
})

// ── 5. Création d'un cabinet ─────────────────────────────────────────────────
test('5 — création d’un cabinet : le mot de passe temporaire s’affiche une seule fois', async ({ page }) => {
  // Le provisionnement crée un schéma dédié et y joue les migrations Alembic :
  // compter largement au-delà du délai par défaut de 30 s.
  test.setTimeout(180_000)
  const errors = watchErrors(page)

  await loginSuperAdmin(page)
  await page.getByRole('link', { name: 'Nouveau cabinet' }).click()
  await expect(page.getByRole('heading', { name: 'Nouveau cabinet' })).toBeVisible()

  await page.getByLabel('Nom du cabinet').fill(nouveauCabinet.nom)
  await page.getByLabel('Identifiant (slug)').fill(nouveauCabinet.slug)
  await page.getByLabel('Email de contact').fill(nouveauCabinet.contactEmail)
  await page.getByLabel('Prénom').fill(nouveauCabinet.adminPrenom)
  await page.getByLabel('Nom', { exact: true }).fill(nouveauCabinet.adminNom)
  await page.getByLabel("Email de l'administrateur").fill(nouveauCabinet.adminEmail)

  // Cabinet de test sans 2FA obligatoire : ses comptes doivent pouvoir se
  // reconnecter dans les tests suivants sans passer par l'enrôlement TOTP, qui
  // exige un authentificateur. La 2FA elle-même est couverte ailleurs.
  await page.getByRole('checkbox').uncheck()

  // Logo choisi dès la création. L'envoi n'a lieu qu'APRÈS la création du
  // cabinet, l'endpoint étant indexé par son identifiant.
  await page
    .locator('form input[type="file"]')
    .setInputFiles({ name: 'creation.png', mimeType: 'image/png', buffer: await pngDeTaille(page, 256, 256) })
  await expect(page.locator('.logo-filename')).toHaveText('creation.png')
  await expect(page.locator('.logo-preview-img')).toBeVisible()

  await page.getByRole('button', { name: 'Créer le cabinet' }).click()

  // Modale téléportée dans `body`.
  const modale = page.locator('.modal-overlay')
  await expect(modale.getByRole('heading', { name: 'Cabinet créé' })).toBeVisible({ timeout: 60_000 })
  await expect(modale.locator('.created-line')).toContainText(nouveauCabinet.nom)
  await expect(modale.locator('.created-line')).toContainText(nouveauCabinet.slug)

  // Le logo est passé : aucun avertissement d'échec partiel n'est affiché.
  await expect(modale.locator('.warn-box--logo')).toHaveCount(0)

  // Le mot de passe temporaire est affiché en clair et signalé comme non récupérable.
  await expect(modale.locator('.warn-box')).toContainText('plus jamais affiché')
  const codePwd = modale.locator('.temp-pwd-code')
  await expect(codePwd).toBeVisible()
  nouveauCabinet.tempPassword = ((await codePwd.textContent()) || '').trim()
  expect(nouveauCabinet.tempPassword.length, 'mot de passe temporaire non vide').toBeGreaterThan(7)
  await expect(modale.locator('.cred-value')).toHaveText(nouveauCabinet.adminEmail)

  await modale.getByRole('button', { name: "J'ai noté le mot de passe" }).click()

  // Redirection vers la fiche du cabinet — on y récupère son identifiant.
  await expect(page).toHaveURL(/\/super-admin\/cabinets\/[0-9a-f-]{36}$/)
  nouveauCabinet.id = page.url().split('/').pop()!
  await expect(page.getByRole('heading', { name: nouveauCabinet.nom })).toBeVisible()

  // Le logo posé à la création est bien rattaché au cabinet.
  await expect(page.locator('.logo-preview-img')).toBeVisible()

  // Le mot de passe n'est plus récupérable une fois la modale fermée.
  await expect(page.locator('.temp-pwd-code')).toHaveCount(0)
  await page.reload()
  await expect(page.locator('.temp-pwd-code')).toHaveCount(0)
  expect(await page.content()).not.toContain(nouveauCabinet.tempPassword)

  expectNoErrors(errors, 'création de cabinet')
})

// ── 6. Étanchéité des sessions ───────────────────────────────────────────────
test('6 — les sessions cabinet et Super-Admin ne se marchent pas dessus', async ({ page, browser }) => {
  const errors = watchErrors(page)

  // a0) Sans session, les routes protégées restent fermées. La page de blocage
  //     `compte-suspendu` est atteignable sans jeton d'accès (le cabinet suspendu
  //     n'en obtient pas) : elle ne doit pas pour autant ouvrir la plateforme à un
  //     visiteur anonyme.
  const ctxAnonyme = await (browser as Browser).newContext()
  const pageAnonyme = await ctxAnonyme.newPage()
  for (const route of ['/', '/parametres', '/compte-suspendu']) {
    await pageAnonyme.goto(route)
    await expect(pageAnonyme, `route ${route} sans session`).toHaveURL(/\/login$/)
  }
  await ctxAnonyme.close()

  // a) Session cabinet seule : rien en sessionStorage pour la console.
  await loginCabinet(page, NOTAIRE_EMAIL, NOTAIRE_PWD)
  await expect(page.locator('.sidebar .logo-title')).toHaveText(DEMO_NOM)
  expect(await page.evaluate(() => window.localStorage.getItem('auth'))).toBeTruthy()
  expect(await page.evaluate(() => window.sessionStorage.getItem('super-admin'))).toBeNull()

  // b) Un utilisateur de cabinet ne peut pas atteindre la console.
  await gotoStable(page, '/super-admin')
  await expect(page).toHaveURL(/\/super-admin\/login$/)
  await expect(page.getByRole('heading', { name: "Console d'exploitation" })).toBeVisible()

  // c) La session cabinet survit à la tentative : elle n'a pas été purgée.
  await gotoStable(page, '/')
  await expect(page.locator('.sidebar .logo-title')).toHaveText(DEMO_NOM)

  // d) Les deux sessions coexistent dans le même navigateur, chacune dans son magasin.
  await loginSuperAdmin(page)
  const magasins = await page.evaluate(() => ({
    cabinet: window.localStorage.getItem('auth'),
    console: window.sessionStorage.getItem('super-admin'),
    consoleEnLocal: window.localStorage.getItem('super-admin'),
  }))
  expect(magasins.console, 'jeton Super-Admin en sessionStorage').toBeTruthy()
  expect(magasins.consoleEnLocal, 'jeton Super-Admin absent de localStorage').toBeNull()
  expect(magasins.cabinet, 'session cabinet préservée').toBeTruthy()

  // e) La session cabinet reste opérationnelle après connexion à la console.
  await gotoStable(page, '/')
  await expect(page.locator('.sidebar .logo-title')).toHaveText(DEMO_NOM)

  expectNoErrors(errors, 'étanchéité des sessions')
})

// ── 7. Suspension → bandeau + page de blocage → réactivation ─────────────────
test('7 — suspension du cabinet créé : bandeau, page de blocage, puis réactivation', async ({ page, browser }) => {
  test.skip(!nouveauCabinet.id, 'le cabinet de test n’a pas pu être créé (test 5)')
  // Parcours long : deux contextes navigateur et quatre changements de statut.
  test.setTimeout(180_000)
  const errorsConsole = watchErrors(page)

  // a) Activation du cabinet créé (il naît en statut « configuration »).
  await loginSuperAdmin(page)
  await setStatutDepuisConsole(page, nouveauCabinet.id, 'Activer')
  await expect(page.locator('.badge')).toHaveText('En production')

  // b) Première connexion de son administrateur : mot de passe temporaire à changer.
  const ctxCabinet: BrowserContext = await (browser as Browser).newContext()
  const pageCabinet = await ctxCabinet.newPage()
  const errorsCabinet = watchErrors(pageCabinet)

  await loginCabinet(pageCabinet, nouveauCabinet.adminEmail, nouveauCabinet.tempPassword)
  await expect(pageCabinet).toHaveURL(/\/auth\/change-password$/)
  await pageCabinet.locator('#current').fill(nouveauCabinet.tempPassword)
  await pageCabinet.locator('#new').fill(nouveauCabinet.nouveauPassword)
  await pageCabinet.locator('#confirm').fill(nouveauCabinet.nouveauPassword)
  await pageCabinet.locator('button[type="submit"]').click()

  await expect(pageCabinet).toHaveURL(/\/$/)
  // Le branding suit bien le cabinet nouvellement créé, pas le cabinet `demo`.
  await expect(pageCabinet.locator('.sidebar .logo-title')).toHaveText(nouveauCabinet.nom)

  // c) Suspension depuis la console.
  const motif = 'Régularisation administrative en attente.'
  await setStatutDepuisConsole(page, nouveauCabinet.id, 'Suspendre', motif)
  await expect(page.locator('.badge')).toHaveText('Suspendu')

  // d) Côté cabinet : l'accès est bloqué, avec le message de régularisation.
  await pageCabinet.goto('/kyc')
  await expect(pageCabinet).toHaveURL(/\/compte-suspendu$/)
  await expect(pageCabinet.getByRole('heading', { name: 'Accès suspendu' })).toBeVisible()
  await expect(pageCabinet.locator('.info-val--mono')).toHaveText(nouveauCabinet.slug)
  await expect(pageCabinet.locator('.badge')).toHaveText('Suspendu')
  await expect(pageCabinet.locator('.suspended-help')).toContainText('administrateur de la plateforme')

  // Le bandeau global signale la suspension sur toutes les vues.
  await expect(pageCabinet.locator('.tenant-banner')).toContainText('Cabinet suspendu')

  // Message de régularisation. Le motif saisi dans la console reste interne à
  // l'exploitation : aucun endpoint ne l'expose au cabinet (ni /auth/*, ni
  // /tenant/me). L'utilisateur reçoit le message générique du portier, qui lui
  // indique la marche à suivre.
  await expect(pageCabinet.locator('.alert-motif')).toContainText(
    "Contactez l'administrateur de la plateforme",
  )

  // e) Le blocage tient aussi sur une navigation SPA (sans rechargement).
  await pageCabinet.getByRole('button', { name: 'Vérifier à nouveau' }).click()
  await expect(pageCabinet).toHaveURL(/\/compte-suspendu$/)

  // f) Réactivation depuis la console.
  await setStatutDepuisConsole(page, nouveauCabinet.id, 'Activer')
  await expect(page.locator('.badge')).toHaveText('En production')

  // g) L'utilisateur retrouve l'accès sans se reconnecter.
  await pageCabinet.getByRole('button', { name: 'Vérifier à nouveau' }).click()
  await expect(pageCabinet).toHaveURL(/\/$/)
  await expect(pageCabinet.locator('.tenant-banner')).toHaveCount(0)
  await expect(pageCabinet.locator('.sidebar .logo-title')).toHaveText(nouveauCabinet.nom)

  expectNoErrors(errorsCabinet, 'suspension — côté cabinet')
  expectNoErrors(errorsConsole, 'suspension — côté console')
  await ctxCabinet.close()
})

// ═══════════════════════════════════════════════════════════════════════════
// Logo du cabinet (tests 8 à 12)
//
// Le cabinet `demo` retrouve son état initial : le test 11 supprime le logo posé
// par le test 9, ce qui rend la série rejouable.
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Fabrique un PNG de la taille demandée, sans fixture binaire au dépôt.
 * L'encodage est délégué au `<canvas>` du navigateur piloté par le test.
 */
async function pngDeTaille(page: Page, largeur: number, hauteur: number): Promise<Buffer> {
  const dataUrl = await page.evaluate(
    ({ w, h }) => {
      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')!
      ctx.fillStyle = '#1a2b45'
      ctx.fillRect(0, 0, w, h)
      ctx.fillStyle = '#c9a227'
      ctx.fillRect(w * 0.25, h * 0.25, w * 0.5, h * 0.5)
      return canvas.toDataURL('image/png')
    },
    { w: largeur, h: hauteur },
  )
  return Buffer.from(dataUrl.split(',')[1], 'base64')
}

/** Dépose un fichier dans l'input caché de l'encart logo de la page Paramètres. */
async function envoyerLogo(page: Page, contenu: Buffer, nom = 'logo.png') {
  await page
    .locator('.logo-section input[type="file"]')
    .setInputFiles({ name: nom, mimeType: 'image/png', buffer: contenu })
}

// ── 8. Titre du tableau de bord ──────────────────────────────────────────────
test('8 — le tableau de bord est titré « Tableau de bord — <cabinet> »', async ({ page }) => {
  const errors = watchErrors(page)

  await loginCabinet(page, NOTAIRE_EMAIL, NOTAIRE_PWD)

  const titre = page.locator('.dashboard .page-title')
  await expect(titre).toHaveText(`Tableau de bord — ${DEMO_NOM}`)

  // Le titre survit à un rechargement (réhydratation du store + /tenant/me).
  await page.reload()
  await expect(titre).toHaveText(`Tableau de bord — ${DEMO_NOM}`)

  expectNoErrors(errors, 'titre du tableau de bord')
})

/**
 * Connexion en tant qu'ADMINISTRATEUR d'un cabinet.
 *
 * Les routes PUT/DELETE du logo dépendent de `require_user_manager`, qui
 * n'autorise que le rôle `admin` (ADM-01). Le cabinet de démonstration n'expose
 * pas de mot de passe d'admin utilisable (il est généré au provisionnement), on
 * s'appuie donc sur l'administrateur du cabinet créé aux tests 5 et 7.
 */
async function loginAdminCabinetCree(page: Page) {
  await loginCabinet(page, nouveauCabinet.adminEmail, nouveauCabinet.nouveauPassword)
}

// ── 9. Envoi d'un logo valide ────────────────────────────────────────────────
test('9 — un logo valide s’envoie depuis Paramètres et apparaît dans la barre latérale', async ({ page }) => {
  test.skip(!nouveauCabinet.id, 'le cabinet de test n’a pas pu être créé (test 5)')
  const errors = watchErrors(page)

  await loginAdminCabinetCree(page)

  // Le logo posé à la création (test 5) est déjà servi dans la barre latérale.
  await expect(page.locator('.sidebar .logo-img')).toBeVisible()
  await expect(page.locator('.sidebar .logo-mark')).toHaveCount(0)

  await page.goto('/parametres')
  const section = page.locator('.logo-section')
  await expect(section.getByRole('heading', { name: 'Logo du cabinet' })).toBeVisible()

  // Les contraintes sont rappelées AVANT l'envoi, et proviennent de l'API.
  const regles = section.locator('.logo-rules')
  await expect(regles).toContainText('PNG')
  await expect(regles).toContainText('1 Mo')
  await expect(regles).toContainText('64×64')
  await expect(regles).toContainText('2048×2048')
  await expect(regles).toContainText('4:1')

  await envoyerLogo(page, await pngDeTaille(page, 240, 160))

  // Le message de confirmation reprend les dimensions retenues par le serveur.
  await expect(section.locator('.save-msg')).toHaveText('Logo enregistré (240×160 px).')
  await expect(section.locator('.logo-preview-img')).toBeVisible()

  // Répercussion immédiate dans la barre latérale, sans rechargement.
  const logoBarre = page.locator('.sidebar .logo-img')
  await expect(logoBarre).toBeVisible()
  await expect(page.locator('.sidebar .logo-mark')).toHaveCount(0)

  // L'image est bien servie (URL d'objet alimentée par un blob non vide).
  const dimensions = await logoBarre.evaluate((el) => {
    const img = el as HTMLImageElement
    return { naturalWidth: img.naturalWidth, src: img.src }
  })
  expect(dimensions.naturalWidth, 'image réellement décodée').toBeGreaterThan(0)
  expect(dimensions.src, 'image servie par URL d’objet, pas par /api/tenant/logo').toContain('blob:')

  // Le logo survit à un rechargement complet.
  await page.reload()
  await expect(page.locator('.sidebar .logo-img')).toBeVisible()

  expectNoErrors(errors, 'envoi d’un logo valide')
})

// ── 10. Refus d'une image non conforme ───────────────────────────────────────
test('10 — une image non conforme est refusée avec un message lisible', async ({ page }) => {
  test.skip(!nouveauCabinet.id, 'le cabinet de test n’a pas pu être créé (test 5)')
  const errors = watchErrors(page)

  await loginAdminCabinetCree(page)
  await page.goto('/parametres')
  const section = page.locator('.logo-section')
  await expect(section).toBeVisible()

  // a) Image plus petite que le minimum de 64×64.
  await envoyerLogo(page, await pngDeTaille(page, 32, 32), 'trop-petit.png')
  const message = section.locator('.save-msg')
  await expect(message).toHaveClass(/msg--err/)
  await expect(message).toContainText('32×32')
  await expect(message).toContainText('64×64')

  // b) Proportions au-delà du rapport 4:1.
  await envoyerLogo(page, await pngDeTaille(page, 1200, 100), 'trop-allonge.png')
  await expect(message).toHaveClass(/msg--err/)
  await expect(message).toContainText('4:1')

  // Le logo précédemment enregistré (test 9) n'a pas été perdu par ces refus.
  await expect(section.locator('.logo-preview-img')).toBeVisible()
  await expect(page.locator('.sidebar .logo-img')).toBeVisible()

  expectNoErrors(errors, 'refus d’un logo non conforme')
})

// ── 11. Suppression du logo ──────────────────────────────────────────────────
test('11 — la suppression du logo fait retomber la barre latérale sur l’icône générique', async ({ page }) => {
  test.skip(!nouveauCabinet.id, 'le cabinet de test n’a pas pu être créé (test 5)')
  const errors = watchErrors(page)

  await loginAdminCabinetCree(page)
  await page.goto('/parametres')
  const section = page.locator('.logo-section')
  await expect(section.locator('.logo-preview-img')).toBeVisible()

  await section.getByRole('button', { name: 'Supprimer' }).click()

  await expect(section.locator('.save-msg')).toHaveText('Logo supprimé.')
  await expect(section.locator('.logo-preview-vide')).toHaveText('Aucun logo')
  await expect(section.locator('.logo-preview-img')).toHaveCount(0)

  // Retour à l'icône générique, sans image cassée ni erreur de console.
  await expect(page.locator('.sidebar .logo-mark')).toBeVisible()
  await expect(page.locator('.sidebar .logo-img')).toHaveCount(0)

  await page.reload()
  await expect(page.locator('.sidebar .logo-mark')).toBeVisible()

  expectNoErrors(errors, 'suppression du logo')
})

// ── 12a. Le notaire principal voit l'encart en lecture seule ─────────────────
test('12 — le notaire principal voit l’aperçu du logo sans bouton de gestion', async ({ page }) => {
  const errors = watchErrors(page)

  await loginCabinet(page, NOTAIRE_EMAIL, NOTAIRE_PWD)
  await page.goto('/parametres')

  const section = page.locator('.logo-section')
  await expect(section).toBeVisible()

  // L'aperçu et le rappel des contraintes restent visibles…
  await expect(section.locator('.logo-preview')).toBeVisible()
  await expect(section.locator('.logo-rules')).toContainText('PNG')

  // … mais aucun moyen d'agir : l'API réserve PUT/DELETE au rôle `admin`
  // (require_user_manager / ADM-01), afficher les boutons promettrait un 403.
  await expect(section.getByRole('button')).toHaveCount(0)
  await expect(section.locator('input[type="file"]')).toHaveCount(0)
  await expect(section.locator('.read-only-notice')).toContainText('seul un administrateur')

  expectNoErrors(errors, 'notaire principal — encart logo en lecture seule')
})

// ── 12b. Un clerc ne dispose d'aucun moyen de modifier le logo ───────────────
test('13 — un clerc voit le branding mais n’a aucun bouton de gestion du logo', async ({ page }) => {
  const errors = watchErrors(page)

  await loginCabinet(page, CLERC_EMAIL, CLERC_PWD)

  // Le branding du cabinet lui est bien servi (l'endpoint de lecture est ouvert
  // à tous les rôles authentifiés).
  await expect(page.locator('.sidebar .logo-title')).toHaveText(DEMO_NOM)
  await expect(page.locator('.dashboard .page-title')).toHaveText(`Tableau de bord — ${DEMO_NOM}`)

  // La page Paramètres est fermée aux clercs par le routeur (meta.roles) : la
  // redirection ramène au tableau de bord, donc aucun bouton de gestion du logo
  // n'est atteignable.
  await gotoStable(page, '/parametres')
  await expect(page).toHaveURL(/\/$/)
  await expect(page.locator('.logo-section')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /logo/i })).toHaveCount(0)

  // Le lien « Paramètres » n'est pas non plus proposé dans la navigation.
  await expect(page.locator('.sidebar .nav-item', { hasText: 'Paramètres' })).toHaveCount(0)

  expectNoErrors(errors, 'clerc — aucun bouton de gestion du logo')
})

// ── 14. Console Super-Admin : pose, remplacement et retrait du logo ──────────
test('14 — la console Super-Admin pose, remplace et retire le logo d’un cabinet', async ({ page, browser }) => {
  test.skip(!nouveauCabinet.id, 'le cabinet de test n’a pas pu être créé (test 5)')
  const errors = watchErrors(page)

  await loginSuperAdmin(page)
  await page.goto(`/super-admin/cabinets/${nouveauCabinet.id}`)

  const carte = page.locator('.card').filter({ has: page.getByRole('heading', { name: 'Logo du cabinet' }) })
  await expect(carte).toBeVisible()

  // Contraintes rappelées ici aussi, depuis /api/super-admin/logo/contraintes.
  await expect(carte.locator('.logo-rules')).toContainText('PNG')
  await expect(carte.locator('.logo-rules')).toContainText('4:1')
  await expect(carte.locator('.logo-preview-vide')).toHaveText('Aucun logo')

  const deposer = async (buffer: Buffer, nom: string) => {
    await carte.locator('input[type="file"]').setInputFiles({ name: nom, mimeType: 'image/png', buffer })
  }

  // a) Pose d'un logo valide.
  await deposer(await pngDeTaille(page, 200, 200), 'console.png')
  await expect(carte.locator('.logo-msg')).toHaveText('Logo enregistré (200×200 px).')
  await expect(carte.locator('.logo-preview-img')).toBeVisible()

  // b) Refus d'une image non conforme — la fiche reste sur le logo précédent.
  await deposer(await pngDeTaille(page, 40, 40), 'trop-petit.png')
  await expect(carte.locator('.logo-msg')).toHaveClass(/logo-msg--err/)
  await expect(carte.locator('.logo-msg')).toContainText('64×64')
  await expect(carte.locator('.logo-preview-img')).toBeVisible()

  // c) Remplacement : l'aperçu suit, grâce au « cache-buster » sur l'horodatage.
  await deposer(await pngDeTaille(page, 300, 120), 'remplacement.png')
  await expect(carte.locator('.logo-msg')).toHaveText('Logo enregistré (300×120 px).')

  // d) Le cabinet voit le logo posé par la console, sans intervention de sa part.
  const ctxCabinet: BrowserContext = await (browser as Browser).newContext()
  const pageCabinet = await ctxCabinet.newPage()
  const errorsCabinet = watchErrors(pageCabinet)
  await loginCabinet(pageCabinet, nouveauCabinet.adminEmail, nouveauCabinet.nouveauPassword)
  await expect(pageCabinet.locator('.sidebar .logo-img')).toBeVisible()

  // e) Retrait depuis la console.
  await carte.getByRole('button', { name: 'Supprimer' }).click()
  await expect(carte.locator('.logo-msg')).toHaveText('Logo supprimé.')
  await expect(carte.locator('.logo-preview-vide')).toHaveText('Aucun logo')
  await page.reload()
  await expect(carte.locator('.logo-preview-vide')).toHaveText('Aucun logo')

  // f) Côté cabinet, retour à l'icône générique après rechargement.
  await pageCabinet.reload()
  await expect(pageCabinet.locator('.sidebar .logo-mark')).toBeVisible()

  expectNoErrors(errorsCabinet, 'console — répercussion côté cabinet')
  expectNoErrors(errors, 'console — gestion du logo')
  await ctxCabinet.close()
})
