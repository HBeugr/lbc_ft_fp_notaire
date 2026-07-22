#!/bin/bash
# Recette SaaS de bout en bout, contre une API réellement démarrée.
#
# Complète la suite pytest : celle-ci exerce la pile ASGI en process, ce script
# exerce le service tel qu'il tourne (démarrage, privilèges DOS posés au boot,
# sérialisation HTTP réelle, codes de statut vus par le navigateur). Le bug
# « PostgreSQL n'accepte pas de paramètre lié dans du DDL » n'était visible que
# par ce chemin.
#
# Parcours : console d'exploitation → provisioning d'un cabinet → portier avant
# activation → activation → connexion → changement de mot de passe imposé →
# isolation vis-à-vis d'un autre cabinet → étanchéité de la console →
# suspension/réactivation → métriques.
#
# Prérequis : API démarrée, annuaire migré, cabinet de démonstration amorcé
# (`python seed_platform.py --demo`).
#
#   API=http://127.0.0.1:8000 bash scripts/e2e_saas.sh
set -u
API=${API:-http://127.0.0.1:8099}
PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
ko()   { echo "  ❌ $1 — $2"; FAIL=$((FAIL+1)); }
check(){ [ -n "$2" ] && [ "$2" = "$3" ] && ok "$1" || ko "$1" "attendu $3, obtenu ${2:-<vide>}"; }

# Extraction d'un champ JSON imbriqué : chemin passé en arguments successifs.
jqv() { python3 -c '
import sys, json
d = json.load(sys.stdin)
for k in sys.argv[1:]:
    d = d[k] if isinstance(d, dict) else ""
print(d if d is not None else "")
' "$@" 2>/dev/null; }

echo "── 1. Console d'exploitation ──────────────────────────────────────────"
SA=$(curl -s -X POST $API/api/super-admin/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"superadmin@plateforme.local","password":"SuperAdmin2026!"}')
SA_TOKEN=$(echo "$SA" | jqv access_token)
[ -n "$SA_TOKEN" ] && ok "connexion Super-Admin" || ko "connexion Super-Admin" "$SA"

echo "── 2. Provisioning d'un cabinet ───────────────────────────────────────"
SUF=$RANDOM
NEW=$(curl -s -X POST $API/api/super-admin/tenants -H "Authorization: Bearer $SA_TOKEN" \
  -H 'Content-Type: application/json' -d "{
    \"nom_cabinet\":\"Étude E2E $SUF\",\"slug\":\"e2e-$SUF\",
    \"contact_email\":\"contact-$SUF@e2e.ci\",\"admin_email\":\"admin-$SUF@e2e.ci\",
    \"admin_first_name\":\"Ada\",\"admin_last_name\":\"Koffi\",\"totp_required\":false}")
TID=$(echo "$NEW" | jqv tenant id)
TPWD=$(echo "$NEW" | jqv admin_temp_password)
SCHEMA_STATUT=$(echo "$NEW" | jqv tenant statut)
[ -n "$TID" ] && ok "cabinet provisionné ($TID)" || ko "provisioning" "$NEW"
check "naît en statut configuration" "$SCHEMA_STATUT" "configuration"

echo "── 3. Portier : cabinet non activé ────────────────────────────────────"
LOGIN_KO=$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/api/auth/login \
  -H 'Content-Type: application/json' -d "{\"email\":\"admin-$SUF@e2e.ci\",\"password\":\"$TPWD\"}")
check "connexion refusée avant activation" "$LOGIN_KO" "403"

echo "── 4. Activation ──────────────────────────────────────────────────────"
ACT=$(curl -s -X POST $API/api/super-admin/tenants/$TID/activate -H "Authorization: Bearer $SA_TOKEN")
check "mise en production" "$(echo "$ACT" | jqv statut)" "production"

echo "── 5. Connexion au cabinet ────────────────────────────────────────────"
LOGIN=$(curl -s -X POST $API/api/auth/login -H 'Content-Type: application/json' \
  -d "{\"email\":\"admin-$SUF@e2e.ci\",\"password\":\"$TPWD\"}")
TOKEN=$(echo "$LOGIN" | jqv access_token)
check "cabinet renvoyé au login" "$(echo "$LOGIN" | jqv tenant id)" "$TID"
[ -n "$TOKEN" ] && ok "jeton émis" || ko "jeton" "$LOGIN"

echo "── 5bis. Changement du mot de passe imposé ────────────────────────────"
# Le mot de passe initial est connu de l'exploitant : tant qu'il n'est pas
# changé, tout endpoint métier doit répondre 403. C'est vérifié ici avant de
# poursuivre — sinon la suite testerait un compte à moitié activé.
BLOQUE=$(curl -s -o /dev/null -w '%{http_code}' $API/api/tenant/me -H "Authorization: Bearer $TOKEN")
check "accès bloqué tant que le mot de passe initial n'est pas changé" "$BLOQUE" "403"
NEWPWD="CabinetE2E-$SUF!x"
CHG=$(curl -s -X PATCH $API/api/auth/password -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"current_password\":\"$TPWD\",\"new_password\":\"$NEWPWD\"}")
TOKEN=$(echo "$CHG" | jqv access_token)
[ -n "$TOKEN" ] && ok "mot de passe changé, nouveau jeton" || ko "changement de mot de passe" "$CHG"

echo "── 6. Contexte cabinet ────────────────────────────────────────────────"
ME=$(curl -s $API/api/tenant/me -H "Authorization: Bearer $TOKEN")
check "/tenant/me renvoie le bon cabinet" "$(echo "$ME" | jqv id)" "$TID"
check "pays exposé" "$(echo "$ME" | jqv pays)" "CI"

echo "── 7. Isolation vis-à-vis du cabinet de démonstration ─────────────────"
DEMO=$(curl -s -X POST $API/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"notaire@notaire.local","password":"Notaire2026!"}')
DEMO_TOKEN=$(echo "$DEMO" | jqv access_token)
DEMO_TID=$(echo "$DEMO" | jqv tenant id)
[ "$DEMO_TID" != "$TID" ] && ok "les deux cabinets sont distincts" || ko "cabinets" "identiques"

U_NEW=$(curl -s $API/api/users -H "Authorization: Bearer $TOKEN" | jqv total)
U_DEMO=$(curl -s $API/api/users -H "Authorization: Bearer $DEMO_TOKEN" | jqv total)
check "cabinet neuf : 1 utilisateur" "$U_NEW" "1"
[ "$U_DEMO" -ge 4 ] 2>/dev/null && ok "cabinet démo : $U_DEMO utilisateurs (indépendant)" \
  || ko "cabinet démo" "obtenu $U_DEMO"

echo "── 8. Jeton forgé vers un autre cabinet ───────────────────────────────"
FORGE=$(curl -s -o /dev/null -w '%{http_code}' $API/api/dossiers \
  -H "Authorization: Bearer $DEMO_TOKEN" -H "X-Tenant-Id: $TID")
check "en-tête X-Tenant-Id ignoré (le jeton fait foi)" "$FORGE" "200"

echo "── 9. Étanchéité de la console ────────────────────────────────────────"
CROSS=$(curl -s -o /dev/null -w '%{http_code}' $API/api/super-admin/tenants \
  -H "Authorization: Bearer $TOKEN")
check "jeton cabinet refusé sur la console" "$CROSS" "401"
BIZ=$(curl -s -o /dev/null -w '%{http_code}' $API/api/dossiers -H "Authorization: Bearer $SA_TOKEN")
check "jeton d'exploitation refusé sur le métier" "$BIZ" "401"

echo "── 10. Suspension puis réactivation ───────────────────────────────────"
curl -s -X POST $API/api/super-admin/tenants/$TID/suspend -H "Authorization: Bearer $SA_TOKEN" \
  -H 'Content-Type: application/json' -d '{"motif":"Test E2E"}' > /dev/null
sleep 1
SUSP=$(curl -s -o /dev/null -w '%{http_code}' $API/api/dossiers -H "Authorization: Bearer $TOKEN")
check "accès coupé (402)" "$SUSP" "402"
DEMO_OK=$(curl -s -o /dev/null -w '%{http_code}' $API/api/dossiers -H "Authorization: Bearer $DEMO_TOKEN")
check "l'autre cabinet reste servi" "$DEMO_OK" "200"
curl -s -X POST $API/api/super-admin/tenants/$TID/activate -H "Authorization: Bearer $SA_TOKEN" > /dev/null
sleep 1
BACK=$(curl -s -o /dev/null -w '%{http_code}' $API/api/dossiers -H "Authorization: Bearer $TOKEN")
check "accès rétabli sans perte" "$BACK" "200"

echo "── 10bis. Flux SSE : le cabinet survit à la sortie du middleware ──────"
# Régression la plus insidieuse de la migration : le générateur SSE est consommé
# APRÈS que le middleware a rendu la main, donc hors du contexte cabinet. Chaque
# lecture repartait alors sur le schéma par défaut. L'échec était SILENCIEUX —
# HTTP 200, mais flux vide. On inspecte donc le CONTENU, pas le statut.
SSE=$(curl -s --max-time 6 "$API/api/alertes/stream?token=$DEMO_TOKEN" 2>/dev/null | head -c 200)
case "$SSE" in
  *"event: count"*) ok "flux SSE alimenté (contexte cabinet conservé)" ;;
  *": error"*)      ko "flux SSE" "le flux signale une erreur interne — contexte cabinet perdu" ;;
  *)                ko "flux SSE" "aucun événement reçu : ${SSE:-<vide>}" ;;
esac

echo "── 11. Métriques d'exploitation ───────────────────────────────────────"
MET=$(curl -s $API/api/super-admin/tenants/$TID/metrics -H "Authorization: Bearer $SA_TOKEN")
check "volumétrie remontée" "$(echo "$MET" | jqv utilisateurs_total)" "1"

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  E2E : $PASS réussis, $FAIL échoués"
echo "════════════════════════════════════════════════════════════════════════"
[ "$FAIL" -eq 0 ]
