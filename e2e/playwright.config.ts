import { defineConfig } from '@playwright/test'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

// 1) Charge .env.e2e (gitignoré) s'il existe — n'écrase pas les valeurs déjà définies,
//    et ignore les valeurs vides (pour laisser le seed prendre le relais).
const envPath = resolve(__dirname, '.env.e2e')
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, 'utf8').split('\n')) {
    if (line.trim().startsWith('#')) continue
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/)
    if (m) {
      const [, k, raw] = m
      const v = raw.replace(/^["']|["']$/g, '').trim()
      if (v && process.env[k] === undefined) process.env[k] = v
    }
  }
}

// 2) Source de vérité : les identifiants dev sont dans backend/seed_admin.py (versionné).
//    On les lit au runtime pour rendre la suite autonome, sans jamais coder de mot de passe.
//    Lignes du type : ("admin@notaire.local", "Admin", "Système", "admin", "Admin2026!"),
const ROLE_TO_PREFIX: Record<string, string> = {
  admin: 'ADMIN',
  notaire_principal: 'NOTAIRE',
  responsable_conformite: 'RC',
  clercs: 'CLERC',
  declarant_centif: 'DC',
  autre_utilisateur: 'AUTRE',
}
const seedPath = resolve(__dirname, '..', 'backend', 'seed_admin.py')
if (existsSync(seedPath)) {
  const seed = readFileSync(seedPath, 'utf8')
  const re = /\(\s*"([^"]+@[^"]+)"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,\s*"([a-z_]+)"\s*,\s*"([^"]+)"\s*\)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(seed)) !== null) {
    const [, email, role, pwd] = m
    const p = ROLE_TO_PREFIX[role]
    if (!p) continue
    if (process.env[`E2E_${p}_EMAIL`] === undefined) process.env[`E2E_${p}_EMAIL`] = email
    if (process.env[`E2E_${p}_PWD`] === undefined) process.env[`E2E_${p}_PWD`] = pwd
  }
}

export default defineConfig({
  testDir: __dirname,
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://149.202.59.47:4000',
    trace: 'off',
    extraHTTPHeaders: { 'Content-Type': 'application/json' },
  },
})
