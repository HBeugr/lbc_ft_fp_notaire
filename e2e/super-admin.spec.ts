/**
 * Parcours complet de la console d'exploitation — de la connexion à la
 * déconnexion, en passant par les fonctions ajoutées : mot de passe forcé,
 * tableau de bord d'agrégat, édition d'un cabinet, 2FA, révocation du jeton.
 *
 * Test navigateur (et non API) : l'essentiel de ce qui est vérifié ici est du
 * ressort du garde de route et du store, invisibles depuis l'API seule.
 *
 * Prérequis : stack lancée et `python seed_platform.py` joué.
 *   SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD peuvent surcharger les défauts.
 */
import { test, expect, type Page } from '@playwright/test'

const EMAIL = process.env.SUPER_ADMIN_EMAIL || 'superadmin@lbcft.com'
const PWD = process.env.SUPER_ADMIN_PASSWORD || 'superAdmin_2026!'

// Mot de passe conforme à la politique (12+, majuscule, minuscule, chiffre,
// spécial). Le test le remet ensuite à sa valeur d'origine pour rester rejouable.
const NOUVEAU_PWD = 'Exploitation2026#Test'

async function tenterConnexion(page: Page, motDePasse: string) {
  await page.goto('/super-admin/login')
  await page.locator('#sa-email').fill(EMAIL)
  await page.locator('#sa-password').fill(motDePasse)
  await page.getByRole('button', { name: /se connecter/i }).click()
  // La console rend soit le shell, soit une alerte d'erreur : on attend la
  // sortie du formulaire plutôt qu'un délai arbitraire.
  await page
    .waitForURL(/\/super-admin(?!\/login)/, { timeout: 5000 })
    .catch(() => undefined)
  return !/\/super-admin\/login/.test(page.url())
}

/**
 * Connexion idempotente. Le mot de passe du Super-Admin change au cours de la
 * suite (c'est précisément ce qu'on teste) et une exécution interrompue peut
 * laisser l'un ou l'autre en base : on essaie les deux plutôt que de supposer
 * un état de départ, sans quoi la suite n'est rejouable qu'après reseed.
 */
async function seConnecter(page: Page, prefere = PWD) {
  const secours = prefere === PWD ? NOUVEAU_PWD : PWD
  if (await tenterConnexion(page, prefere)) return prefere
  if (await tenterConnexion(page, secours)) return secours
  throw new Error(
    `Connexion Super-Admin impossible avec les deux mots de passe connus (${EMAIL}). ` +
      'Rejouez `python seed_platform.py` ou fixez SUPER_ADMIN_PASSWORD.'
  )
}

/** Ramène le compte au mot de passe passé en argument, quel que soit l'état courant. */
async function fixerMotDePasse(page: Page, cible: string) {
  const actuel = await seConnecter(page, cible)
  if (actuel === cible) return
  await page.goto('/super-admin/compte')
  await page.locator('#current').fill(actuel)
  await page.locator('#next').fill(cible)
  await page.locator('#confirm').fill(cible)
  await page.getByRole('button', { name: /changer le mot de passe/i }).click()
  await page.getByText(/mot de passe modifié/i).waitFor({ timeout: 5000 })
}

test.describe('Console Super-Admin', () => {
  test('le lien depuis la connexion cabinet mène à la console', async ({ page }) => {
    await page.goto('/login')
    const lien = page.getByRole('link', { name: /acc(è|e)s super-administrateur/i })
    await expect(lien).toBeVisible()
    await lien.click()
    await expect(page).toHaveURL(/\/super-admin\/login/)
  })

  test('un mauvais mot de passe est refusé avec un message explicite', async ({ page }) => {
    const entre = await tenterConnexion(page, 'MauvaisMotDePasse1!')
    expect(entre).toBe(false)
    await expect(page.getByRole('alert')).toContainText(/incorrect/i)
    await expect(page).toHaveURL(/\/super-admin\/login/)
  })

  test('la console est inaccessible sans session', async ({ page }) => {
    await page.goto('/super-admin')
    await expect(page).toHaveURL(/\/super-admin\/login/)
  })

  /**
   * Le verrou ne s'observe que sur un compte fraîchement seedé : une fois le
   * mot de passe changé, `must_change_password` est définitivement à faux et
   * aucun endpoint ne permet de le remettre. Le test s'annonce ignoré plutôt
   * que de mentir sur une exécution répétée.
   */
  test('le mot de passe initial verrouille la console sur « Mon compte »', async ({ page }) => {
    const actuel = await seConnecter(page)
    test.skip(
      actuel !== PWD || !/\/super-admin\/compte/.test(page.url()),
      'Mot de passe déjà changé sur ce compte — rejouer le seed pour tester le verrou.'
    )

    await expect(page.getByRole('heading', { name: /mon compte/i })).toBeVisible()

    // Toute tentative de sortie ramène ici tant que rien n'est changé.
    await page.goto('/super-admin')
    await expect(page).toHaveURL(/\/super-admin\/compte/)

    await page.locator('#current').fill(PWD)
    await page.locator('#next').fill(NOUVEAU_PWD)
    await page.locator('#confirm').fill(NOUVEAU_PWD)
    await page.getByRole('button', { name: /changer le mot de passe/i }).click()

    // Le verrou levé, la console doit EMMENER l'utilisateur au tableau de bord.
    // Sans cette redirection il restait sur une page inchangée, libre d'en
    // sortir mais sans aucun signe le lui indiquant — ce qui se lisait comme un
    // blocage. C'est le défaut remonté en production.
    await expect(page).toHaveURL(/\/super-admin$/)
    await expect(page.getByRole('heading', { name: /tableau de bord/i })).toBeVisible()
  })

  test('parcours complet : connexion → dashboard → cabinets → déconnexion', async ({ page }) => {
    await seConnecter(page)

    // ── Tableau de bord ─────────────────────────────────────────────────
    await page.goto('/super-admin')
    await expect(page).toHaveURL(/\/super-admin$/)
    await expect(page.getByRole('heading', { name: /tableau de bord/i })).toBeVisible()

    // Les 5 cartes, alignées sur la console de l'assujetti. Portée limitée à
    // <main> : « Cabinets » existe aussi dans la barre de navigation.
    const contenu = page.getByRole('main')
    for (const carte of ['Cabinets', 'Utilisateurs', 'Actifs', 'En configuration', 'Suspendus']) {
      await expect(contenu.getByText(carte, { exact: true })).toBeVisible()
    }

    // Aucune trace de 2FA ne doit subsister sur la console.
    await expect(page.getByText(/double authentification/i)).toHaveCount(0)

    // Le CTA de création, absent jusqu'ici du tableau de bord.
    await expect(contenu.getByRole('link', { name: /nouveau cabinet/i })).toBeVisible()

    // ── 5. Navigation vers la liste des cabinets ────────────────────────
    await page.getByRole('link', { name: /^cabinets$/i }).click()
    await expect(page).toHaveURL(/\/super-admin\/cabinets/)
    await expect(page.getByRole('heading', { name: /cabinets notariaux/i })).toBeVisible()

    // ── 6. Déconnexion : le jeton doit être révoqué côté serveur ────────
    // On capture le jeton avant, pour vérifier ensuite qu'il ne passe plus.
    const jeton = await page.evaluate(() => {
      const brut = sessionStorage.getItem('super-admin')
      return brut ? JSON.parse(brut).accessToken : null
    })
    expect(jeton).toBeTruthy()

    await page.getByRole('button', { name: /se déconnecter/i }).click()
    await expect(page).toHaveURL(/\/super-admin\/login/)

    // Le jeton révoqué est refusé — sans cela, « se déconnecter » ne serait
    // qu'un effacement de session côté navigateur.
    const reponse = await page.request.get('/api/super-admin/auth/me', {
      headers: { Authorization: `Bearer ${jeton}` },
    })
    expect(reponse.status()).toBe(401)
  })

  test('édition d’un cabinet et réinitialisation de l’accès administrateur', async ({ page }) => {
    await seConnecter(page)
    await page.goto('/super-admin/cabinets')

    const premier = page.locator('table tbody tr a').first()
    await expect(premier).toBeVisible()
    await premier.click()
    await expect(page).toHaveURL(/\/super-admin\/cabinets\//)

    // ── Édition : le champ « Identifiant » doit rester verrouillé, il nomme
    //    le schéma PostgreSQL du cabinet.
    await page.getByRole('button', { name: /^modifier$/i }).click()
    await expect(page.locator('#e-slug')).toBeDisabled()

    // Numéro varié à chaque exécution : réenregistrer une valeur identique
    // laisserait le service sans modification à appliquer.
    const nouveauTel = `+225 07${String(Date.now()).slice(-8)}`
    await page.locator('#e-tel').fill(nouveauTel)
    await page.getByRole('button', { name: /enregistrer/i }).click()

    // Remonte le message du serveur plutôt qu'un « formulaire toujours ouvert »,
    // qui n'apprend rien sur la cause.
    // `.alert-error` existe à plusieurs endroits de la fiche : on les lit toutes
    // plutôt que d'en cibler une, sous peine de violer le mode strict.
    const messages = (await page.locator('.alert-error').allInnerTexts())
      .map((t) => t.trim())
      .filter(Boolean)
    if (messages.length) {
      throw new Error(`Enregistrement refusé : ${messages.join(' | ')}`)
    }

    // Retour en lecture avec la valeur persistée.
    await expect(page.locator('#e-tel')).toHaveCount(0)
    await expect(page.getByText(nouveauTel)).toBeVisible()

    // ── Réinitialisation de l'accès admin : confirmation puis mot de passe
    //    temporaire affiché une seule fois.
    await page.getByRole('button', { name: /réinitialiser le mot de passe administrateur/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('button', { name: /^réinitialiser$/i }).click()

    await expect(page.getByText(/nouveau mot de passe temporaire/i)).toBeVisible()
    await expect(page.getByText(/ne sera plus jamais affiché/i)).toBeVisible()
  })

  test('la page « Mon compte » ne propose aucune 2FA', async ({ page }) => {
    await seConnecter(page)
    await page.goto('/super-admin/compte')

    await expect(page.getByRole('heading', { name: /mot de passe/i })).toBeVisible()
    await expect(page.getByText(/double authentification/i)).toHaveCount(0)
    await expect(page.getByRole('button', { name: /activer/i })).toHaveCount(0)
    await expect(page.locator('canvas.qr')).toHaveCount(0)
  })

  test('la 2FA n’est plus exposée par l’API', async ({ page, request }) => {
    await seConnecter(page)
    const jeton = await page.evaluate(() => {
      const brut = sessionStorage.getItem('super-admin')
      return brut ? JSON.parse(brut).accessToken : null
    })

    // Les endpoints retirés doivent renvoyer 404 — pas 401 ni 405, qui
    // signaleraient une route encore montée.
    for (const chemin of ['setup', 'activate', 'verify', 'verify-backup', 'disable']) {
      const reponse = await request.post(`/api/super-admin/auth/totp/${chemin}`, {
        headers: { Authorization: `Bearer ${jeton}` },
        data: { code: '000000' },
        failOnStatusCode: false,
      })
      expect(reponse.status(), `/auth/totp/${chemin}`).toBe(404)
    }
  })

  test('une ligne du tableau de bord ouvre la fiche du cabinet', async ({ page }) => {
    await seConnecter(page)
    await page.goto('/super-admin')

    const ligne = page.getByRole('main').locator('table tbody tr').first()
    await expect(ligne).toBeVisible()
    // Le clic porte sur la cellule de statut, donc hors du nom du cabinet :
    // c'est bien la ligne entière qui doit être cliquable, pas le seul lien.
    await ligne.locator('td').nth(2).click()
    await expect(page).toHaveURL(/\/super-admin\/cabinets\/[0-9a-f-]{36}/)
  })

  test.afterAll(async ({ browser }) => {
    // Remet le mot de passe d'origine pour que la suite reste rejouable.
    // Confort, pas assertion : un échec ici ne doit pas faire passer la suite
    // pour cassée — `seConnecter` sait de toute façon retrouver l'état réel.
    const page = await browser.newPage()
    try {
      await fixerMotDePasse(page, PWD)
    } catch {
      // Ignoré volontairement, cf. ci-dessus.
    } finally {
      await page.close().catch(() => undefined)
    }
  })
})
