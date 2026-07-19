"""Recette de conformité au CDC — volet 3/3.

Périmètre : Module 7 (Administration, et surtout la matrice de permissions §7.3),
Module 8 (Déclaration d'Opération Suspecte) et Module 9 (Révision périodique du
KYC), plus la section 5 « Sécurité & Conformité ».

Référence : cahier des charges LBC/FT/FP notarial, adossé à l'Ordonnance
N°2023-875 du 23 novembre 2023.

────────────────────────────────────────────────────────────────────────────────
Convention de lecture des tests de permissions
────────────────────────────────────────────────────────────────────────────────
La matrice §7.3 décrit une AUTORISATION, pas un résultat métier. Ces tests
vérifient donc uniquement le franchissement du contrôle d'accès :

    O (autorisé)  → la réponse n'est PAS 403 (200/201/404/409/422 conviennent :
                    la requête a passé le RBAC, seul point contrôlé ici)
    N (interdit)  → la réponse EST 403

Ce choix est délibéré. Exiger un 200 obligerait à construire un état métier
complet et valide pour chacune des ~30 actions × 4 rôles, ce qui déplacerait le
test hors de son objet et le rendrait fragile. FastAPI résout les dépendances
(dont le RBAC) avant de valider le corps de requête : un rôle interdit reçoit
donc bien 403 même sur une charge utile incomplète.

Les cas partiels (P¹, P², P³) ne se réduisent pas à un code HTTP : ils font
l'objet de tests dédiés en fin de section.
"""
import io
import uuid
from datetime import date, timedelta

import pytest

from tests.conftest import auth_headers, create_alerte, create_dossier, create_user

pytestmark = pytest.mark.asyncio(loop_scope="session")


# Les quatre rôles applicatifs du CDC (§2 « Utilisateurs Cibles »).
ROLES = ("admin", "notaire_principal", "responsable_conformite", "clercs")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 7 §7.3 — MATRICE DE PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
#
# Transcription littérale du tableau du CDC. Légende : O = autorisé,
# N = interdit, P = partiel (contrainte non réductible à un code HTTP, traitée
# par un test dédié plus bas).
#
# L'ordre des colonnes suit celui du CDC : Admin | Notaire Principal |
# Resp. Conformité | Clercs.

MATRICE: dict[str, dict[str, str]] = {
    # ── KYC ───────────────────────────────────────────────────────────────────
    "KYC-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "O"},
    "KYC-02": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "O"},
    "KYC-03": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "O"},
    "KYC-04": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "KYC-05": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "P"},
    "KYC-06": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    # ── Scoring ───────────────────────────────────────────────────────────────
    "SCO-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "P"},
    "SCO-02": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
    # SCO-03 « Modifier les seuils de classification » vaut N pour TOUS les rôles,
    # Administrateur compris. Il n'existe donc aucun endpoint à appeler : la règle
    # est vérifiée par `test_sco03_seuils_verrouilles_pour_tous`.
    # ── Alertes ───────────────────────────────────────────────────────────────
    "ALE-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "ALE-02": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "ALE-03": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    # ── Workflow ──────────────────────────────────────────────────────────────
    "WRK-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "O"},
    "WRK-02": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "WRK-03": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "WRK-04": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "N", "clercs": "N"},
    "WRK-05": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "WRK-06": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "O"},
    # ── DOS ───────────────────────────────────────────────────────────────────
    "DOS-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "O"},
    "DOS-02": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "DOS-03": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "DOS-04": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "DOS-05": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "N", "clercs": "N"},
    # ── Registres ─────────────────────────────────────────────────────────────
    "REG-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "REG-02": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    # ── Reporting ─────────────────────────────────────────────────────────────
    "RPT-01": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "P"},
    "RPT-02": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    "RPT-03": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "O", "clercs": "N"},
    # ── Administration ────────────────────────────────────────────────────────
    "ADM-01": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
    "ADM-02": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
    "ADM-03": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
    "ADM-04": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
    "ADM-05": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
    "ADM-06": {"admin": "O", "notaire_principal": "O", "responsable_conformite": "N", "clercs": "N"},
    "ADM-07": {"admin": "O", "notaire_principal": "N", "responsable_conformite": "N", "clercs": "N"},
}


# Écarts assumés vis-à-vis du CDC, matérialisés par un `xfail(strict=True)`.
# Strict est important : le jour où le code devient conforme, le test « xpasse »
# et la suite échoue, ce qui force à retirer la dérogation plutôt qu'à la laisser
# dormir. La clé est le couple (code, rôle).
ECARTS_CDC: dict[tuple[str, str], str] = {
    ("WRK-05", "clercs"): (
        "ÉCART CDC §7.3 — WRK-05 « Assigner un dossier » vaut N pour les Clercs, mais "
        "la chaîne d'assignation implémentée (décision produit datée du 2026-07-15, "
        "commentaire dans dossiers.py) autorise le clerc à router son dossier vers le "
        "Notaire Principal et à se l'auto-assigner. Divergence fonctionnelle assumée, "
        "à arbitrer : soit le CDC est amendé, soit la chaîne est refermée."
    ),
    ("DOS-01", "notaire_principal"): (
        "ÉCART CDC §7.3 — DOS-01 « Signaler une suspicion (flag interne) » vaut O pour "
        "les quatre rôles. `_SIGNALEUR_ROLES` de alertes.py ne contient que "
        "(clercs, admin) : le Notaire Principal ne peut pas déposer de flag interne. "
        "Permission trop ÉTROITE — gêne fonctionnelle, pas un défaut de sécurité."
    ),
    ("DOS-01", "responsable_conformite"): (
        "ÉCART CDC §7.3 — DOS-01 vaut O pour le Responsable Conformité ; "
        "`_SIGNALEUR_ROLES` l'exclut. Même cause que ci-dessus."
    ),
    ("ALE-01", "clercs"): (
        "ÉCART CDC §7.3 — ALE-01 « Consulter les alertes » vaut N pour les Clercs. "
        "GET /api/alertes leur répond 200, avec un périmètre restreint aux alertes de "
        "leurs propres dossiers assignés (cf. `scope_assigned` dans alertes.py). "
        "L'écart n'est PAS refermé ici, et ce pour une raison précise : "
        "`test_alignment.py::test_alertes_cloisonnement_non_superviseur` — fichier hors "
        "du périmètre de cette recette — exige explicitement ce 200 et vérifie le "
        "cloisonnement par dossier. Les deux attentes sont contradictoires et doivent "
        "être arbitrées par le métier : soit le CDC est amendé pour reconnaître une "
        "consultation restreinte (cohérente avec P¹ et avec le devoir de signalement du "
        "clerc, Art. 60), soit l'endpoint est fermé et le test d'alignement révisé. "
        "Ce n'est pas une fuite de données : le cloisonnement par dossier est effectif."
    ),
}


# Acteurs réutilisés par la matrice, un par rôle.
#
# Créer un compte par cas (≈ 120) n'apporte rien — ces tests vérifient une
# AUTORISATION et ne modifient jamais le compte qu'ils utilisent — mais gonfle
# l'annuaire du cabinet de test de plusieurs centaines d'entrées. Or
# `user_repo.get_all` trie sur `last_name`, que les fixtures laissent identique
# pour tous : au-delà de la première page (50), l'ordre entre ex æquo n'est plus
# garanti et un test voisin qui cherche « son » utilisateur dans la liste ne le
# trouve plus. L'effet de bord a été observé sur
# `test_tenant_isolation.py::test_utilisateurs_disjoints`. On mutualise donc.
_ACTEURS: dict[str, object] = {}


async def _acteur(db, role: str):
    """Acteur mutualisé pour `role` dans le cabinet de test par défaut."""
    if role not in _ACTEURS:
        _ACTEURS[role] = await create_user(db, role=role)
    return _ACTEURS[role]


def _dossier_payload() -> dict:
    return {
        "type_client": "PP",
        "type_operation": "vente_immobiliere",
        "nb_parties": 1,
        "montant_transaction": 1_000_000,
        "mode_paiement": "virement",
    }


async def _executer_action(code: str, client, db, acteur):
    """Exerce l'endpoint qui porte le code d'action `code` au nom de `acteur`.

    Chaque branche construit le strict minimum d'état métier : on ne teste ici
    que le franchissement du contrôle d'accès (cf. en-tête de module).
    """
    h = auth_headers(acteur)

    # ── KYC ───────────────────────────────────────────────────────────────────
    if code == "KYC-01":  # Créer une fiche client
        return await client.post("/api/dossiers", headers=h, json=_dossier_payload())

    if code == "KYC-02":  # Modifier une fiche en cours de saisie
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="brouillon")
        # Corps VALIDE : le contrôle KYC-04 s'exerce dans le corps de l'endpoint,
        # donc après la validation Pydantic. Une charge utile incomplète
        # renverrait 422 avant d'avoir seulement atteint le contrôle d'accès, et
        # le test ne prouverait rien.
        return await client.put(
            f"/api/dossiers/{d.id}/kyc/pp", headers=h, json={"nom": "Kouassi", "prenoms": "Yao"}
        )

    if code == "KYC-03":  # Uploader des documents
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="brouillon")
        return await client.post(
            f"/api/dossiers/{d.id}/documents",
            headers=h,
            files={"file": ("piece.txt", io.BytesIO(b"piece identite"), "text/plain")},
            data={"type_document": "piece_identite"},
        )

    if code == "KYC-04":  # Modifier une fiche VALIDÉE
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="valide")
        # Corps VALIDE : le contrôle KYC-04 s'exerce dans le corps de l'endpoint,
        # donc après la validation Pydantic. Une charge utile incomplète
        # renverrait 422 avant d'avoir seulement atteint le contrôle d'accès, et
        # le test ne prouverait rien.
        return await client.put(
            f"/api/dossiers/{d.id}/kyc/pp", headers=h, json={"nom": "Kouassi", "prenoms": "Yao"}
        )

    if code == "KYC-05":  # Consulter une fiche
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id)
        return await client.get(f"/api/dossiers/{d.id}", headers=h)

    if code == "KYC-06":  # Exporter une fiche PDF
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id)
        return await client.post(
            "/api/rapports/client", headers=h, json={"dossier_reference": d.reference}
        )

    # ── Scoring ───────────────────────────────────────────────────────────────
    if code == "SCO-01":  # Consulter un score
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id)
        return await client.post(
            f"/api/dossiers/{d.id}/scoring/calculate", headers=h, json={"axes": {}}
        )

    if code == "SCO-02":  # Modifier les pondérations des axes
        return await client.put("/api/scoring/weights", headers=h, json={"weights": {"secteur": 1.0}})

    # ── Alertes ───────────────────────────────────────────────────────────────
    if code == "ALE-01":  # Consulter les alertes
        return await client.get("/api/alertes", headers=h)

    if code == "ALE-02":  # Traiter une alerte
        d = await create_dossier(db, created_by=acteur.id)
        a = await create_alerte(db, dossier_id=d.id)
        return await client.patch(
            f"/api/alertes/{a.id}/traiter", headers=h,
            json={"statut": "traitee", "resolution_note": "Recette CDC"},
        )

    if code == "ALE-03":  # Bloquer un dossier manuellement
        d = await create_dossier(db, created_by=acteur.id)
        a = await create_alerte(db, dossier_id=d.id)
        return await client.post(f"/api/alertes/{a.id}/bloquer-dossier", headers=h)

    # ── Workflow ──────────────────────────────────────────────────────────────
    if code == "WRK-01":  # Soumettre un dossier en analyse
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="brouillon")
        return await client.patch(
            f"/api/dossiers/{d.id}/statut", headers=h,
            params={"new_statut": "en_analyse", "commentaire": "Soumission recette"},
        )

    if code == "WRK-02":  # Valider un dossier
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="en_analyse")
        return await client.patch(
            f"/api/dossiers/{d.id}/statut", headers=h,
            params={"new_statut": "valide", "commentaire": "Validation recette"},
        )

    if code == "WRK-03":  # Exiger une vigilance renforcée
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="en_analyse")
        return await client.patch(
            f"/api/dossiers/{d.id}/statut", headers=h,
            params={"new_statut": "vigilance_renforcee", "commentaire": "Vigilance recette"},
        )

    if code == "WRK-04":  # Clôturer un dossier
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id, statut="traite")
        return await client.patch(
            f"/api/dossiers/{d.id}/statut", headers=h,
            params={"new_statut": "cloture", "commentaire": "Cloture recette"},
        )

    if code == "WRK-05":  # Assigner un dossier
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id)
        cible = await _acteur(db, "notaire_principal")
        return await client.patch(
            f"/api/dossiers/{d.id}/assign", headers=h, params={"user_id": cible.id}
        )

    if code == "WRK-06":  # Ajouter un commentaire interne
        d = await create_dossier(db, created_by=acteur.id, assigned_to=acteur.id)
        return await client.post(
            f"/api/dossiers/{d.id}/commentaires", headers=h, json={"contenu": "Note interne recette"}
        )

    # ── DOS ───────────────────────────────────────────────────────────────────
    if code == "DOS-01":  # Signaler une suspicion (flag interne) — Art. 60
        return await client.post(
            "/api/alertes/signaler", headers=h, json={"description": "Suspicion recette CDC"}
        )

    if code == "DOS-02":  # Initier un DOS
        d = await create_dossier(db, created_by=acteur.id)
        return await client.post("/api/dos", headers=h, json={"dossier_id": d.id})

    if code == "DOS-03":  # Rédiger et valider un DOS
        d = await create_dossier(db, created_by=acteur.id)
        dos = await _creer_dos(client, db, d.id)
        return await client.put(
            f"/api/dos/{dos['id']}", headers=h, json={"indices_blanchiment": "Recette CDC"}
        )

    if code == "DOS-04":  # Consulter les DOS existants
        return await client.get("/api/dos", headers=h)

    if code == "DOS-05":  # Exporter un DOS en PDF
        d = await create_dossier(db, created_by=acteur.id)
        dos = await _creer_dos(client, db, d.id)
        return await client.get(f"/api/dos/{dos['id']}/pdf", headers=h)

    # ── Registres ─────────────────────────────────────────────────────────────
    if code == "REG-01":  # Consulter les registres
        return await client.get("/api/registres/kyc", headers=h)

    if code == "REG-02":  # Exporter les registres
        return await client.get("/api/registres/kyc/export", headers=h, params={"format": "excel"})

    # ── Reporting ─────────────────────────────────────────────────────────────
    if code == "RPT-01":  # Consulter les tableaux de bord
        return await client.get("/api/dashboard/stats", headers=h)

    if code == "RPT-02":  # Générer des rapports
        return await client.post("/api/rapports/conformite", headers=h, json={})

    if code == "RPT-03":  # Exporter des rapports
        return await client.post("/api/rapports/audit", headers=h, json={})

    # ── Administration ────────────────────────────────────────────────────────
    if code == "ADM-01":  # Gérer les utilisateurs
        return await client.post(
            "/api/users", headers=h,
            json={
                "email": f"adm01_{uuid.uuid4().hex[:8]}@test.ci",
                "first_name": "Recette", "last_name": "CDC",
                "role": "clercs", "password": "TestPass123!",
            },
        )

    if code == "ADM-02":  # Modifier rôles et permissions
        cible = await create_user(db, role="clercs")
        return await client.patch(
            f"/api/users/{cible.id}", headers=h, json={"role": "responsable_conformite"}
        )

    if code == "ADM-03":  # Modifier la matrice de risque (pondérations des axes)
        return await client.put(
            "/api/scoring/weights", headers=h, json={"weights": {"intermediaires": 1.0}}
        )

    if code == "ADM-04":  # Modifier les seuils d'alerte (seuil espèces T2)
        return await client.put(
            "/api/scoring/weights", headers=h, json={"seuil_especes_t2_fcfa": 15_000_000}
        )

    if code == "ADM-05":  # Mettre à jour les listes de sanctions
        return await client.post(
            "/api/sanctions/upload", headers=h,
            data={"nom": "Recette CDC", "type_liste": "OFAC"},
            files={"file": ("liste.csv", io.BytesIO(b"nom,alias\nDoe John,JD\n"), "text/csv")},
        )

    if code == "ADM-06":  # Consulter les logs
        return await client.get("/api/audit/logs", headers=h)

    if code == "ADM-07":  # Configurer les paramètres système
        return await client.get("/api/tenant/quota", headers=h)

    raise AssertionError(f"Code d'action non implémenté dans la recette : {code}")


def _texte_pdf(contenu: bytes) -> str:
    """Texte lisible d'un PDF fpdf2, flux compressés compris.

    fpdf2 compresse les flux de contenu par défaut : chercher une chaîne
    directement dans les octets du PDF ne prouverait rien — le test passerait
    même si la mention interdite y figurait.
    """
    import re
    import zlib

    morceaux: list[str] = [contenu.decode("latin-1", errors="ignore")]
    for flux in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", contenu, re.DOTALL):
        try:
            morceaux.append(zlib.decompress(flux).decode("latin-1", errors="ignore"))
        except zlib.error:
            continue
    return "\n".join(morceaux)


async def _creer_dos(client, db, dossier_id: str) -> dict:
    """Crée une DOS via l'API au nom d'un Responsable Conformité (rôle habilité)."""
    rc = await _acteur(db, "responsable_conformite")
    r = await client.post("/api/dos", headers=auth_headers(rc), json={"dossier_id": dossier_id})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize(
    ("code", "role"),
    [(c, r) for c in MATRICE for r in ROLES if MATRICE[c][r] != "P"],
)
async def test_matrice_permissions_7_3(code, role, client, db):
    """CDC §7.3 — une ligne de la matrice, un rôle, une vérification.

    Fondement réglementaire : Art. 12 de l'Ordonnance N°2023-875 (organisation et
    contrôle interne, séparation des fonctions).
    """
    if (code, role) in ECARTS_CDC:
        pytest.xfail(ECARTS_CDC[(code, role)])

    attendu = MATRICE[code][role]
    acteur = await _acteur(db, role)
    reponse = await _executer_action(code, client, db, acteur)

    if attendu == "N":
        assert reponse.status_code == 403, (
            f"{code} doit être INTERDIT au rôle « {role} » (CDC §7.3) — "
            f"reçu {reponse.status_code}. Une permission trop large est un défaut "
            f"de séparation des fonctions (Art. 12). Corps : {reponse.text[:300]}"
        )
    else:
        assert reponse.status_code != 403, (
            f"{code} doit être AUTORISÉ au rôle « {role} » (CDC §7.3) — "
            f"reçu 403. Corps : {reponse.text[:300]}"
        )


# ── Cas partiels de la matrice ────────────────────────────────────────────────

async def test_kyc05_p1_clerc_limite_aux_dossiers_assignes(client, db):
    """P¹ — Clercs : consultation limitée aux dossiers qui leur sont assignés."""
    clerc = await _acteur(db, "clercs")
    autre = await create_user(db, role="clercs")
    mien = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    etranger = await create_dossier(db, created_by=autre.id, assigned_to=autre.id)

    h = auth_headers(clerc)
    assert (await client.get(f"/api/dossiers/{mien.id}", headers=h)).status_code == 200
    assert (await client.get(f"/api/dossiers/{etranger.id}", headers=h)).status_code == 403

    # La liste ne doit pas non plus laisser filtrer le dossier d'autrui.
    listing = await client.get("/api/dossiers", headers=h, params={"page_size": 200})
    assert listing.status_code == 200
    references = {d["id"] for d in listing.json()["items"]}
    assert mien.id in references
    assert etranger.id not in references, "P¹ violé : un clerc voit un dossier non assigné."


async def test_kyc05_p1_superviseurs_voient_tout(client, db):
    """P¹ ne s'applique qu'aux Clercs : les trois superviseurs ont KYC-05 = O."""
    clerc = await _acteur(db, "clercs")
    dossier = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    for role in ("admin", "notaire_principal", "responsable_conformite"):
        superviseur = await _acteur(db, role)
        r = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(superviseur))
        assert r.status_code == 200, f"{role} doit consulter tout dossier (KYC-05 = O)."


async def test_sco01_p2_clerc_label_sans_detail_des_axes(client, db):
    """P² — Clercs : score en label seul (Faible/Moyen/Élevé), jamais le détail des axes."""
    clerc = await _acteur(db, "clercs")
    dossier = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)

    r = await client.post(
        f"/api/dossiers/{dossier.id}/scoring/calculate",
        headers=auth_headers(clerc),
        json={"axes": {"secteur": 2, "coherence_doc": 2}},
    )
    assert r.status_code == 200, r.text
    corps = r.json()

    assert corps["niveau"] in ("FAIBLE", "MOYEN", "ELEVE"), "Le label de classification reste dû."
    assert corps["axes"] == [], (
        "P² violé : la ventilation axe par axe est exposée à un clerc. "
        "Le CDC réserve le détail des axes à l'analyse de risque."
    )
    assert corps["triggers_actifs"] == [], "P² violé : le détail des triggers est exposé à un clerc."
    assert corps["trigger_principal"] is None, "P² violé : le trigger nominatif est exposé à un clerc."


async def test_sco01_superviseur_conserve_le_detail_des_axes(client, db):
    """Contrôle inverse : le masquage P² ne doit pas amputer le Responsable Conformité."""
    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id)

    r = await client.post(
        f"/api/dossiers/{dossier.id}/scoring/calculate",
        headers=auth_headers(rc),
        json={"axes": {"secteur": 2, "coherence_doc": 2}},
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["axes"]) == 10, "Le superviseur doit voir les 10 axes du CDC §2.4."


async def test_rpt01_p3_clerc_tableau_de_bord_restreint(client, db):
    """P³ — Clercs : tableau de bord limité à leurs dossiers, sans statistiques globales."""
    clerc = await _acteur(db, "clercs")
    autre = await create_user(db, role="clercs")
    await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    await create_dossier(db, created_by=autre.id, assigned_to=autre.id)

    r = await client.get("/api/dashboard/stats", headers=auth_headers(clerc))
    assert r.status_code == 200, r.text
    corps = r.json()

    assert corps["scope"] == "assigne", "P³ violé : le clerc obtient un périmètre non restreint."
    # Les agrégats de cabinet sont réservés aux superviseurs.
    for cle_globale in ("dossiers_by_statut", "risque_distribution"):
        assert cle_globale not in corps, (
            f"P³ violé : la statistique globale « {cle_globale} » est servie à un clerc."
        )
    # DOS-04 + Art. 63 : aucun volume déclaratif du cabinet ne doit transiter.
    assert corps.get("dos_ouvertes", 0) == 0, (
        "Art. 63 / DOS-04 violés : le compteur de DOS du cabinet est exposé à un clerc."
    )


async def test_rpt01_superviseur_obtient_les_statistiques_globales(client, db):
    """Contrôle inverse : RPT-01 = O sans restriction pour les superviseurs."""
    rc = await _acteur(db, "responsable_conformite")
    r = await client.get("/api/dashboard/stats", headers=auth_headers(rc))
    assert r.status_code == 200
    corps = r.json()
    assert corps["scope"] == "global"
    assert "risque_distribution" in corps


async def test_sco03_seuils_verrouilles_pour_tous(client, db):
    """SCO-03 — « Modifier les seuils de classification » vaut N pour TOUS les rôles.

    Le CDC §2.2 est explicite : « Les seuils de classification sont verrouillés
    dans le code source et ne peuvent être modifiés par aucun utilisateur, y
    compris l'Administrateur. Seules les pondérations des 10 axes sont
    paramétrables. » La vérification est double : les seuils sont bien des
    constantes du code, et aucune route ne les expose en écriture.
    """
    from app.main import app
    from app.services import scoring_service

    # 1. Les bornes du CDC §2.2 sont figées dans le code source.
    assert scoring_service._SEUILS == {"FAIBLE": (0, 7), "MOYEN": (8, 13), "ELEVE": (14, 20)}
    assert scoring_service._classify(7) == "FAIBLE"
    assert scoring_service._classify(8) == "MOYEN"
    assert scoring_service._classify(13) == "MOYEN"
    assert scoring_service._classify(14) == "ELEVE"

    # 2. Aucune route en écriture ne porte sur les seuils de classification.
    routes_ecriture = {
        (m, r.path)
        for r in app.routes
        for m in getattr(r, "methods", set()) or set()
        if m in {"POST", "PUT", "PATCH", "DELETE"}
    }
    suspectes = [
        (m, p) for m, p in routes_ecriture
        if "seuil" in p.lower() and "classification" in p.lower()
    ]
    assert not suspectes, f"SCO-03 violé : route d'écriture sur les seuils — {suspectes}"

    # 3. L'Administrateur lui-même ne peut pas déplacer les bornes en passant par
    #    l'endpoint des pondérations : celui-ci n'accepte que des poids d'axes et
    #    le seuil espèces T2 (qui, lui, est bien paramétrable — Art. 72).
    admin = await _acteur(db, "admin")
    r = await client.put(
        "/api/scoring/weights",
        headers=auth_headers(admin),
        json={"weights": {"FAIBLE": 99, "MOYEN": 99, "ELEVE": 99}},
    )
    assert r.status_code in (200, 422), r.text
    assert scoring_service._SEUILS == {"FAIBLE": (0, 7), "MOYEN": (8, 13), "ELEVE": (14, 20)}, (
        "SCO-03 violé : les seuils de classification ont bougé après un appel Admin."
    )


async def test_adm06_responsable_conformite_exclu_des_logs(client, db):
    """ADM-06 — « Consulter les logs » : Admin O, Notaire Principal O, RC N, Clercs N.

    Régression gardée : l'endpoint reposait sur `require_rc`, qui laissait passer
    le Responsable Conformité.
    """
    attendu = {"admin": 200, "notaire_principal": 200, "responsable_conformite": 403, "clercs": 403}
    for role, code_attendu in attendu.items():
        acteur = await _acteur(db, role)
        r = await client.get("/api/audit/logs", headers=auth_headers(acteur))
        assert r.status_code == code_attendu, (
            f"ADM-06 : le rôle « {role} » devrait obtenir {code_attendu}, reçu {r.status_code}."
        )


async def test_adm01_notaire_principal_ne_gere_pas_les_utilisateurs(client, db):
    """ADM-01/ADM-02 — la gestion des comptes et des rôles est réservée à l'Admin.

    Séparation des fonctions (Art. 12) : le Notaire Principal valide et clôture
    les dossiers ; lui laisser créer des comptes et distribuer les rôles lui
    permettrait de se constituer un second compte non tracé.
    """
    np = await _acteur(db, "notaire_principal")
    cible = await create_user(db, role="clercs")
    h = auth_headers(np)

    creation = await client.post(
        "/api/users", headers=h,
        json={
            "email": f"np_{uuid.uuid4().hex[:8]}@test.ci", "first_name": "N", "last_name": "P",
            "role": "clercs", "password": "TestPass123!",
        },
    )
    assert creation.status_code == 403, "ADM-01 : le Notaire Principal ne crée pas de compte."

    modification = await client.patch(
        f"/api/users/{cible.id}", headers=h, json={"role": "responsable_conformite"}
    )
    assert modification.status_code == 403, "ADM-02 : le Notaire Principal ne redistribue pas les rôles."

    desactivation = await client.delete(f"/api/users/{cible.id}", headers=h)
    assert desactivation.status_code == 403, "ADM-01 : le Notaire Principal ne désactive pas de compte."

    reinit = await client.post(f"/api/admin/users/{cible.id}/reset-password/temporary", headers=h)
    assert reinit.status_code == 403, "ADM-01 : le Notaire Principal ne réinitialise pas de mot de passe."


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 8 — DÉCLARATION D'OPÉRATION SUSPECTE (DOS)
# ══════════════════════════════════════════════════════════════════════════════

async def test_dos_82_droits_initiation(client, db):
    """§8.2 — Droits d'initiation du DOS.

    Resp. Conformité et Notaire Principal : initier + rédiger + valider + soumettre
    (Art. 100, déclarant désigné). Clercs : signaler uniquement (Art. 60).
    """
    for role in ("responsable_conformite", "notaire_principal", "admin"):
        acteur = await _acteur(db, role)
        dossier = await create_dossier(db, created_by=acteur.id)
        r = await client.post("/api/dos", headers=auth_headers(acteur), json={"dossier_id": dossier.id})
        assert r.status_code == 201, f"§8.2 : « {role} » doit pouvoir initier un DOS — {r.text[:200]}"

    clerc = await _acteur(db, "clercs")
    dossier = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    r = await client.post("/api/dos", headers=auth_headers(clerc), json={"dossier_id": dossier.id})
    assert r.status_code == 403, "§8.2 : un clerc ne peut PAS initier un DOS (Art. 60)."


async def test_dos_82_clerc_peut_signaler_une_suspicion(client, db):
    """§8.2 / Art. 60 — le clerc dispose du flag interne, seule voie qui lui est ouverte."""
    clerc = await _acteur(db, "clercs")
    r = await client.post(
        "/api/alertes/signaler",
        headers=auth_headers(clerc),
        json={"description": "Paiement fractionné inhabituel — recette CDC"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["type_alerte"] == "SIGNALEMENT_INTERNE"


async def test_dos_83_initiation_bloque_le_dossier(client, db):
    """§8.3 étape 3 / Art. 61 — « Dossier bloqué dès initiation du DOS », immédiat."""
    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id, statut="en_analyse")
    assert dossier.statut == "en_analyse"

    r = await client.post("/api/dos", headers=auth_headers(rc), json={"dossier_id": dossier.id})
    assert r.status_code == 201, r.text

    relu = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(rc))
    assert relu.status_code == 200
    assert relu.json()["statut"] == "bloque", (
        "Art. 61 violé : l'initiation d'un DOS doit suspendre l'opération immédiatement."
    )


async def test_dos_83_blocage_journalise(client, db):
    """§8.3 — l'initiation du DOS et le blocage qu'elle entraîne sont journalisés."""
    rc = await _acteur(db, "responsable_conformite")
    admin = await _acteur(db, "admin")
    dossier = await create_dossier(db, created_by=rc.id, statut="en_analyse")

    r = await client.post("/api/dos", headers=auth_headers(rc), json={"dossier_id": dossier.id})
    assert r.status_code == 201

    logs = await client.get(
        "/api/audit/logs", headers=auth_headers(admin), params={"action": "dos.created", "limit": 500}
    )
    assert logs.status_code == 200
    entites = {e["entity_id"] for e in logs.json()["items"]}
    assert r.json()["id"] in entites, "§8.3 : la création du DOS doit laisser une trace d'audit."


async def test_dos_83_justification_de_rejet_obligatoire_et_journalisee(client, db):
    """§8.3 étape 2 — « Justification de rejet obligatoire si refus — journalisée ».

    Le refus se matérialise par le classement sans suite de la déclaration.
    """
    rc = await _acteur(db, "responsable_conformite")
    admin = await _acteur(db, "admin")
    dossier = await create_dossier(db, created_by=rc.id)
    h = auth_headers(rc)

    dos = (await client.post("/api/dos", headers=h, json={"dossier_id": dossier.id})).json()
    await client.put(f"/api/dos/{dos['id']}", headers=h, json={"type_soupcon_bc": True})
    assert (await client.post(f"/api/dos/{dos['id']}/soumettre", headers=h)).status_code == 200

    # Sans motif → refusé.
    sans_motif = await client.post(f"/api/dos/{dos['id']}/classer", headers=h, json={"motif": "   "})
    assert sans_motif.status_code == 422, "§8.3 : le classement sans motif doit être rejeté."

    # Avec motif → accepté et journalisé.
    motif = "Opération justifiée par un acte de succession régulier — recette CDC."
    avec_motif = await client.post(f"/api/dos/{dos['id']}/classer", headers=h, json={"motif": motif})
    assert avec_motif.status_code == 200, avec_motif.text
    assert avec_motif.json()["statut"] == "classee"

    logs = await client.get(
        "/api/audit/logs", headers=auth_headers(admin), params={"action": "dos.classee", "limit": 500}
    )
    traces = [e for e in logs.json()["items"] if e["entity_id"] == dos["id"]]
    assert traces, "§8.3 : le rejet doit être journalisé."
    assert traces[0]["detail"]["motif"] == motif, "§8.3 : la justification doit figurer au journal."


async def test_dos_85_confidentialite_art63_roles_non_habilites(client, db):
    """§8.5 / Art. 63 — aucune information de DOS ne filtre vers un rôle non habilité.

    « Le statut "DOS en cours" est visible uniquement par Responsable conformité,
    Notaire principal et Administrateur. »
    """
    rc = await _acteur(db, "responsable_conformite")
    clerc = await _acteur(db, "clercs")
    dossier = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    dos = (await client.post("/api/dos", headers=auth_headers(rc), json={"dossier_id": dossier.id})).json()

    h_clerc = auth_headers(clerc)
    # Ni la liste, ni la fiche, ni le PDF, ni le registre DOS.
    assert (await client.get("/api/dos", headers=h_clerc)).status_code == 403
    assert (await client.get(f"/api/dos/{dos['id']}", headers=h_clerc)).status_code == 403
    assert (await client.get(f"/api/dos/{dos['id']}/pdf", headers=h_clerc)).status_code == 403
    assert (await client.get("/api/registres/dos", headers=h_clerc)).status_code == 403

    # Le registre DOS ne doit pas non plus être annoncé au clerc dans le catalogue.
    catalogue = await client.get("/api/registres", headers=h_clerc)
    assert catalogue.status_code == 200
    assert "dos" not in {r["id"] for r in catalogue.json()["registres"]}, (
        "Art. 63 : l'existence même du registre DOS ne doit pas être révélée à un clerc."
    )


async def test_dos_85_reference_dos_absente_du_rapport_client(client, db):
    """§8.5 / Art. 63 — « Aucun champ, statut ou mention lié à un DOS ne peut
    apparaître dans tout document exporté destiné au client. »"""
    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id)
    h = auth_headers(rc)
    dos = (await client.post("/api/dos", headers=h, json={"dossier_id": dossier.id})).json()

    rapport = await client.post(
        "/api/rapports/client", headers=h, json={"dossier_reference": dossier.reference}
    )
    assert rapport.status_code == 200, rapport.text

    texte = _texte_pdf(rapport.content)
    # Garde-fou anti-test-vide : si l'extraction ne rend rien, l'absence de
    # mention DOS ne prouverait rien du tout.
    assert dossier.reference in texte, (
        "Extraction PDF inopérante — le test de confidentialité serait vacuant."
    )
    assert dos["reference_interne"] not in texte, (
        "Art. 63 violé : la référence du DOS apparaît dans le rapport client."
    )
    # Recherche par MOT ENTIER : « dos » en sous-chaîne apparaît dans « dossier »,
    # qui est le sujet légitime du rapport. Sans la frontière de mot, le test
    # échouerait sur un document parfaitement conforme.
    import re

    for mention in ("DOS", "soupcon", "soupçon", "suspicion", "suspecte"):
        trouve = re.search(rf"\b{re.escape(mention)}\b", texte, re.IGNORECASE)
        assert trouve is None, (
            f"Art. 63 violé : la mention « {mention} » figure dans un document client."
        )


async def test_dos_05_export_pdf_refuse_au_responsable_conformite(client, db):
    """DOS-05 — l'export PDF d'un DOS est réservé à l'Admin et au Notaire Principal.

    Le Responsable Conformité rédige et valide (DOS-03) mais n'exporte pas : la
    matrice §7.3 lui oppose un N sur DOS-05.
    """
    rc = await _acteur(db, "responsable_conformite")
    np = await _acteur(db, "notaire_principal")
    dossier = await create_dossier(db, created_by=rc.id)
    dos = (await client.post("/api/dos", headers=auth_headers(rc), json={"dossier_id": dossier.id})).json()

    assert (await client.get(f"/api/dos/{dos['id']}/pdf", headers=auth_headers(rc))).status_code == 403
    r_np = await client.get(f"/api/dos/{dos['id']}/pdf", headers=auth_headers(np))
    assert r_np.status_code == 200
    assert r_np.headers["content-type"] == "application/pdf"


async def test_dos_84_dix_sections_centif(client, db):
    """§8.4 — le formulaire guidé reproduit les 10 sections officielles CENTIF-CI."""
    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id)
    h = auth_headers(rc)
    dos = (await client.post("/api/dos", headers=h, json={"dossier_id": dossier.id})).json()

    # Un champ au moins par section normée du CDC §8.4.
    sections = {
        1: "organisme_libelle",          # Organisme déclarant
        2: "reference_interne",          # Informations générales
        3: "type_soupcon_bc",            # Analyse — type de soupçon
        4: "statut_operations",          # Statut des opérations
        5: "detail_transactions",        # Détail des transactions
        6: "indices_blanchiment",        # Indices de blanchiment
        7: "identification",             # Identification des intervenants
        8: "relations_affaires",         # Relations d'affaires
        9: "supports",                   # Supports utilisés
        10: "autres_informations",       # Autres informations
    }
    manquantes = [n for n, champ in sections.items() if champ not in dos]
    assert not manquantes, f"§8.4 : sections CENTIF absentes du formulaire — {manquantes}"

    # Les motifs officiels CENTIF (section 3) sont un champ à cocher structuré.
    assert "motifs" in dos, "§8.4 section 3 : les 14 motifs officiels CENTIF doivent être portés."


async def test_dos_soumission_exige_un_type_de_soupcon(client, db):
    """§8.4 section 3 — le type de soupçon (BC / FT / Prolifération) est obligatoire."""
    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id)
    h = auth_headers(rc)
    dos = (await client.post("/api/dos", headers=h, json={"dossier_id": dossier.id})).json()

    sans = await client.post(f"/api/dos/{dos['id']}/soumettre", headers=h)
    assert sans.status_code == 422, "§8.4 : un DOS sans type de soupçon ne doit pas partir."

    await client.put(f"/api/dos/{dos['id']}", headers=h, json={"type_soupcon_ft": True})
    avec = await client.post(f"/api/dos/{dos['id']}/soumettre", headers=h)
    assert avec.status_code == 200, avec.text


async def test_dos_separation_des_fonctions_art100(client, db):
    """Art. 100 — le signataire de la transmission CENTIF est distinct du valideur.

    Le CDC §8.2 désigne deux acteurs habilités ; la double validation n'a de sens
    que si elle est portée par deux personnes.
    """
    admin = await _acteur(db, "admin")
    np = await _acteur(db, "notaire_principal")
    dossier = await create_dossier(db, created_by=admin.id)
    h_admin = auth_headers(admin)

    dos = (await client.post("/api/dos", headers=h_admin, json={"dossier_id": dossier.id})).json()
    await client.put(f"/api/dos/{dos['id']}", headers=h_admin, json={"type_soupcon_bc": True})
    await client.post(f"/api/dos/{dos['id']}/soumettre", headers=h_admin)
    # L'admin valide en tant que conformité…
    assert (await client.post(f"/api/dos/{dos['id']}/valider", headers=h_admin)).status_code == 200
    # … et ne peut donc pas signer lui-même la transmission.
    auto = await client.post(f"/api/dos/{dos['id']}/transmettre", headers=h_admin)
    assert auto.status_code == 403, "Art. 100 : le valideur ne doit pas pouvoir signer la transmission."
    # Un second acteur habilité, lui, transmet.
    tiers = await client.post(f"/api/dos/{dos['id']}/transmettre", headers=auth_headers(np))
    assert tiers.status_code == 200, tiers.text


async def test_dos_append_only_pas_de_suppression(client, db):
    """§8.5 — « Le DOS et toutes ses pièces sont archivés 10 ans — statut non
    supprimable (Art. 23). » Aucune route de suppression ne doit exister."""
    from app.main import app

    # Le préfixe doit être exact : « /dos » en sous-chaîne attrape aussi
    # /api/dossiers/…, dont les suppressions de bénéficiaires effectifs n'ont
    # rien à voir avec la déclaration de soupçon.
    suppressions = [
        r.path for r in app.routes
        if "DELETE" in (getattr(r, "methods", set()) or set())
        and (r.path == "/api/dos" or r.path.startswith("/api/dos/"))
    ]
    assert not suppressions, f"§8.5 violé : route de suppression de DOS — {suppressions}"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 9 — RÉVISION PÉRIODIQUE DU KYC
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    ("classification", "est_ppe", "trigger", "annees", "base_legale"),
    [
        ("FAIBLE", False, False, 5, "Art. 19"),
        ("MOYEN", False, False, 3, "Art. 19"),
        ("ELEVE", False, False, 2, "Art. 19 + Art. 6"),
        ("FAIBLE", True, False, 3, "Art. 29 — PPE tout niveau"),
        ("ELEVE", True, False, 3, "Art. 29 — PPE tout niveau"),
        ("FAIBLE", False, True, 1, "Art. 19 + Art. 29 — trigger absolutoire actif"),
    ],
)
def test_module9_frequences_reevaluation(classification, est_ppe, trigger, annees, base_legale):
    """§9.1 — Fréquences de réévaluation par classification.

    FAIBLE 5 ans · MOYEN 3 ans · ÉLEVÉ 2 ans · PPE (tout niveau) 3 ans ·
    Trigger absolutoire actif : annuellement, jusqu'à levée du trigger.
    """
    from app.services import revision_service

    depuis = date(2026, 1, 15)
    echeance = revision_service.prochaine_echeance(
        classification, est_ppe=est_ppe, trigger_actif=trigger, depuis=depuis
    )
    assert echeance.year - depuis.year == annees, (
        f"§9.1 ({base_legale}) : {classification} "
        f"{'PPE ' if est_ppe else ''}{'trigger ' if trigger else ''}"
        f"→ {annees} an(s) attendu(s), obtenu {echeance.year - depuis.year}."
    )
    assert (echeance.month, echeance.day) == (depuis.month, depuis.day)


def test_module9_jalons_de_relance():
    """§9.2 — Workflow de réévaluation : J+30 · J+60 · J+90 · J+120, et alerte J-30."""
    from app.services import revision_service

    echeance = date(2026, 6, 1)
    jalons = revision_service.jalons_relance(echeance)
    assert jalons["alerte_j_minus_30"] == echeance - timedelta(days=30)
    assert jalons["relance_1"] == echeance + timedelta(days=30)
    assert jalons["relance_2"] == echeance + timedelta(days=60)
    assert jalons["vigilance_renforcee"] == echeance + timedelta(days=90)
    assert jalons["blocage"] == echeance + timedelta(days=120)


async def test_module9_planification_automatique_a_la_validation(client, db):
    """§9.1 — la validation d'un dossier arme la réévaluation à la bonne échéance.

    Sans planification automatique, l'alerte J-30 et l'escalade §9.2 ne
    s'enclencheraient jamais : l'obligation de vigilance constante (Art. 19)
    resterait lettre morte.
    """
    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(
        db, created_by=rc.id, statut="en_analyse", classification="FAIBLE", score_base=3
    )
    h = auth_headers(rc)

    r = await client.patch(
        f"/api/dossiers/{dossier.id}/statut", headers=h,
        params={"new_statut": "valide", "commentaire": "Validation recette CDC"},
    )
    assert r.status_code == 200, r.text

    revisions = await client.get("/api/revisions", headers=h, params={"limit": 200})
    assert revisions.status_code == 200
    mienne = [x for x in revisions.json() if x["dossier_id"] == dossier.id]
    assert mienne, "§9.1 : aucune réévaluation planifiée à la validation du dossier."

    echeance = date.fromisoformat(mienne[0]["date_echeance"])
    assert echeance.year - date.today().year == 5, (
        "§9.1 : un dossier FAIBLE se réévalue à 5 ans (Art. 19)."
    )
    assert mienne[0]["classification_avant"] == "FAIBLE"
    assert mienne[0]["score_avant"] == 3


async def test_module9_escalade_j90_vigilance_renforcee(client, db):
    """§9.2 — J+90 : « Statut bascule en Vigilance Renforcée », notifié au Resp. Conformité."""
    from app.models.revision import RevisionKyc

    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id, statut="valide")
    from tests.conftest import _scope_of

    with _scope_of(db):
        db.add(RevisionKyc(
            dossier_id=dossier.id,
            date_echeance=date.today() - timedelta(days=95),
            classification_avant="MOYEN",
        ))
        await db.commit()

    r = await client.post("/api/revisions/run-escalade", headers=auth_headers(rc))
    assert r.status_code == 200, r.text
    assert r.json()["vigilance"] >= 1, "§9.2 : l'échéance dépassée de 95 j doit basculer en vigilance."

    relu = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(rc))
    assert relu.json()["statut"] == "vigilance_renforcee"


async def test_module9_escalade_j120_blocage(client, db):
    """§9.2 — J+120 : « Dossier bloqué + suggestion DOS si Élevé »."""
    from app.models.revision import RevisionKyc
    from tests.conftest import _scope_of

    rc = await _acteur(db, "responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id, statut="valide", classification="ELEVE")

    with _scope_of(db):
        db.add(RevisionKyc(
            dossier_id=dossier.id,
            date_echeance=date.today() - timedelta(days=130),
            classification_avant="ELEVE",
        ))
        await db.commit()

    r = await client.post("/api/revisions/run-escalade", headers=auth_headers(rc))
    assert r.status_code == 200, r.text
    assert r.json()["blocage"] >= 1

    relu = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(rc))
    assert relu.json()["statut"] == "bloque", "§9.2 : J+120 doit bloquer le dossier."

    # La suggestion de DOS se matérialise par une alerte ÉLEVÉ sur le dossier.
    alertes = await client.get(
        "/api/alertes", headers=auth_headers(rc), params={"dossier_id": dossier.id, "page_size": 50}
    )
    types = {a["type_alerte"] for a in alertes.json()["items"]}
    assert "REVISION_ECHUE" in types, "§9.2 : l'escalade J+120 doit laisser une alerte."


async def test_module9_tracabilite_reevaluation(client, db):
    """§9.4 — Traçabilité : date de déclenchement, identité, date de validation,
    identité du validateur, score avant et après."""
    rc = await _acteur(db, "responsable_conformite")
    admin = await _acteur(db, "admin")
    dossier = await create_dossier(
        db, created_by=rc.id, statut="valide", classification="MOYEN", score_base=10
    )
    h = auth_headers(rc)

    creation = await client.post(
        "/api/revisions", headers=h,
        json={
            "dossier_id": dossier.id,
            "date_echeance": (date.today() + timedelta(days=30)).isoformat(),
            "assigned_to": rc.id,
        },
    )
    assert creation.status_code == 201, creation.text
    revision = creation.json()
    assert revision["created_at"], "§9.4 : la date de déclenchement doit être portée."
    assert revision["score_avant"] == 10, "§9.4 : le score avant réévaluation doit être figé."
    assert revision["classification_avant"] == "MOYEN"

    validation = await client.post(
        f"/api/revisions/{revision['id']}/valider", headers=h,
        json={"justification": "Pièces d'identité renouvelées — recette CDC"},
    )
    assert validation.status_code == 200, validation.text
    validee = validation.json()
    assert validee["statut"] == "completee"
    assert validee["date_validation"], "§9.4 : la date de validation doit être portée."
    assert validee["valide_par"] == rc.id, "§9.4 : l'identité du validateur doit être portée."
    assert validee["score_apres"] == 10, "§9.4 : le score après réévaluation doit être portée."

    # Journal d'audit — les deux jalons du §9.4 y figurent.
    h_admin = auth_headers(admin)
    for action in ("revision.created", "revision.validee"):
        logs = await client.get(
            "/api/audit/logs", headers=h_admin, params={"action": action, "limit": 500}
        )
        assert logs.status_code == 200
        assert any(e["entity_id"] == revision["id"] for e in logs.json()["items"]), (
            f"§9.4 : l'action « {action} » doit être journalisée."
        )


async def test_module9_reevaluation_reservee_aux_habilites(client, db):
    """§9 — la réévaluation KYC relève du Responsable Conformité (cf. §2)."""
    clerc = await _acteur(db, "clercs")
    dossier = await create_dossier(db, created_by=clerc.id, assigned_to=clerc.id)
    h = auth_headers(clerc)

    creation = await client.post(
        "/api/revisions", headers=h,
        json={"dossier_id": dossier.id, "date_echeance": date.today().isoformat()},
    )
    assert creation.status_code == 403
    assert (await client.get("/api/revisions", headers=h)).status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SÉCURITÉ & CONFORMITÉ
# ══════════════════════════════════════════════════════════════════════════════

# ── 5.1 Authentification ──────────────────────────────────────────────────────

def test_51_2fa_obligatoire_pour_les_roles_sensibles(tenant_a):
    """§5.1 — « 2FA obligatoire pour Notaire principal et Responsable conformité ;
    optionnelle mais recommandée pour les Clercs. »

    La politique est portée par le cabinet (`totp_required`). Le test vérifie la
    règle de rattachement rôle → obligation, cabinet exigeant la 2FA.
    """
    from app.core.tenant_context import TenantContext, tenant_scope
    from app.models.user import User

    cabinet_2fa = TenantContext(
        id=tenant_a.id, schema=tenant_a.schema, slug=tenant_a.slug, nom=tenant_a.nom,
        statut=tenant_a.statut, key_salt=tenant_a.key_salt, totp_required=True,
        storage_bucket=tenant_a.storage_bucket,
    )
    attendu = {
        "notaire_principal": True,
        "responsable_conformite": True,
        "admin": True,          # rôle de supervision — 2FA exigée également
        "clercs": False,        # optionnelle, jamais imposée (§5.1)
    }
    with tenant_scope(cabinet_2fa):
        for role, obligatoire in attendu.items():
            assert User(role=role).requires_2fa is obligatoire, (
                f"§5.1 : la 2FA pour « {role} » devrait être "
                f"{'obligatoire' if obligatoire else 'optionnelle'}."
            )


def test_51_expiration_de_session_30_minutes():
    """§5.1 / Art. 29 — « Expiration de session après 30 minutes d'inactivité. »"""
    from app.core.config import settings

    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30, (
        "§5.1 : la durée de vie du jeton d'accès porte l'expiration de session."
    )


async def test_51_jeton_expire_rejete(client, db):
    """§5.1 — un jeton dont la durée de vie est écoulée n'ouvre plus aucun accès."""
    from datetime import datetime, timezone

    from jose import jwt

    from app.core.config import settings

    utilisateur = await _acteur(db, "responsable_conformite")
    perime = jwt.encode(
        {
            "sub": utilisateur.id,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "type": "access",
            "role": utilisateur.role,
            "tid": db.info["tenant"].id,
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {perime}"})
    assert r.status_code == 401, "§5.1 : un jeton expiré doit être refusé."


async def test_51_2fa_en_attente_bloque_lacces_metier(client, db):
    """§5.1 — tant que le second facteur n'est pas fourni, la session n'ouvre rien."""
    from app.core import security

    utilisateur = await _acteur(db, "notaire_principal")
    jeton = security.create_access_token(
        utilisateur.id,
        extra={"role": utilisateur.role, "totp_pending": True, "tid": db.info["tenant"].id},
    )
    r = await client.get("/api/dossiers", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 403, "§5.1 : une session en attente de 2FA ne doit rien servir."


# ── 5.3 Listes de sanctions ───────────────────────────────────────────────────

async def test_53_mise_a_jour_des_listes_reservee_a_ladmin(client, db):
    """§5.3 / ADM-05 — « Base interne des listes mise à jour manuellement par
    l'Administrateur. »"""
    fichier = {"file": ("liste.csv", io.BytesIO(b"nom,alias\nDoe John,JD\n"), "text/csv")}
    formulaire = {"nom": "Recette CDC", "type_liste": "OFAC"}

    for role in ("notaire_principal", "responsable_conformite", "clercs"):
        acteur = await _acteur(db, role)
        r = await client.post(
            "/api/sanctions/upload", headers=auth_headers(acteur),
            data=formulaire,
            files={"file": ("liste.csv", io.BytesIO(b"nom,alias\nDoe John,JD\n"), "text/csv")},
        )
        assert r.status_code == 403, f"ADM-05 : « {role} » ne met pas à jour les listes."

    admin = await _acteur(db, "admin")
    r = await client.post(
        "/api/sanctions/upload", headers=auth_headers(admin), data=formulaire, files=fichier
    )
    assert r.status_code == 201, r.text


async def test_53_desactivation_de_liste_reservee_a_ladmin(client, db):
    """§5.3 — la désactivation d'une liste relève également de l'Administrateur."""
    rc = await _acteur(db, "responsable_conformite")
    r = await client.patch(
        f"/api/sanctions/{uuid.uuid4()}/deactivate", headers=auth_headers(rc)
    )
    assert r.status_code == 403


def test_53_seuil_de_fraicheur_95_jours():
    """§5.3 — « Une alerte est générée si la mise à jour n'a pas été effectuée
    depuis plus de 95 jours. »"""
    from app.services import sanctions_service

    assert sanctions_service.SANCTIONS_THRESHOLD_DAYS == 95


# ── 5.4 Journalisation & audit ────────────────────────────────────────────────

def test_54_logs_immuables_aucune_route_de_modification():
    """§5.4 — « Logs immuables : aucun rôle ne peut modifier ou supprimer les logs. »

    La garantie se vérifie d'abord par l'absence de surface : aucune route
    d'écriture ne doit exister sur le journal d'audit, pour aucun rôle.
    """
    from app.main import app

    # On vise le routeur du JOURNAL d'audit, et lui seul. Deux faux positifs à
    # écarter : /api/auth/login et /api/auth/logout (qui contiennent « log »),
    # et POST /api/rapports/audit — qui GÉNÈRE un rapport à partir du journal
    # sans jamais y écrire.
    ecritures = [
        (sorted(getattr(r, "methods", set()) or set()), r.path)
        for r in app.routes
        if (getattr(r, "methods", set()) or set()) & {"POST", "PUT", "PATCH", "DELETE"}
        and r.path.startswith("/api/audit")
    ]
    assert not ecritures, f"§5.4 violé : route d'écriture sur le journal d'audit — {ecritures}"


async def test_54_logs_non_modifiables_par_aucun_role(client, db):
    """§5.4 — vérification active : aucun rôle n'obtient de verbe d'écriture sur les logs."""
    admin = await _acteur(db, "admin")
    logs = await client.get("/api/audit/logs", headers=auth_headers(admin), params={"limit": 1})
    assert logs.status_code == 200
    items = logs.json()["items"]
    if not items:
        pytest.skip("Aucune entrée d'audit disponible pour éprouver l'immuabilité.")
    log_id = items[0]["id"]

    for role in ROLES:
        acteur = await _acteur(db, role)
        h = auth_headers(acteur)
        for methode, chemin in (
            ("delete", f"/api/audit/logs/{log_id}"),
            ("patch", f"/api/audit/logs/{log_id}"),
            ("put", f"/api/audit/logs/{log_id}"),
        ):
            r = await getattr(client, methode)(chemin, headers=h)
            assert r.status_code in (403, 404, 405), (
                f"§5.4 violé : {methode.upper()} {chemin} accessible au rôle « {role} » "
                f"(reçu {r.status_code})."
            )


async def test_54_contenu_du_journal(client, db):
    """§5.4 — « Chaque action enregistrée : identifiant utilisateur, rôle, action,
    objet, horodatage UTC, adresse IP. »"""
    admin = await _acteur(db, "admin")
    dossier_cree = await client.post(
        "/api/dossiers", headers=auth_headers(admin), json=_dossier_payload()
    )
    assert dossier_cree.status_code == 201, dossier_cree.text

    logs = await client.get(
        "/api/audit/logs", headers=auth_headers(admin),
        params={"action": "dossier.created", "limit": 500},
    )
    assert logs.status_code == 200
    traces = [e for e in logs.json()["items"] if e["entity_id"] == dossier_cree.json()["id"]]
    assert traces, "§5.4 : la création d'un dossier doit être journalisée."

    trace = traces[0]
    for champ in ("user_id", "user_role", "action", "entity_type", "entity_id", "ip_address", "created_at"):
        assert trace.get(champ), f"§5.4 : le champ « {champ} » manque au journal."
    assert trace["user_id"] == admin.id
    assert trace["user_role"] == "admin"


# ── 5.5 Archivage réglementaire ───────────────────────────────────────────────

async def test_55_suppression_dossier_archive_impossible(db, tenant_a):
    """§5.5 / Art. 23 & 197 — « Suppression physique impossible avant expiration
    des 10 ans — règle implémentée au niveau base de données. »

    La garantie est éprouvée au niveau du SGBD, et non de l'applicatif : c'est
    précisément ce que le CDC exige (« contournement = infraction pénale »).

    La tentative de suppression se fait dans une session DÉDIÉE : le déclencheur
    PostgreSQL avorte la transaction, ce qui laisse la session inutilisable. La
    fixture `db` étant de portée « session », la réutiliser ici contaminerait
    tous les tests suivants — on en ouvre donc une jetable.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.core.database import tenant_session
    from app.core.tenant_context import tenant_scope
    from tests.conftest import _scope_of

    utilisateur = await _acteur(db, "admin")
    archive = await create_dossier(db, created_by=utilisateur.id, statut="archive")

    with tenant_scope(tenant_a):
        async with tenant_session(tenant_a) as jetable:
            with pytest.raises(DBAPIError) as exc:
                await jetable.execute(
                    text("DELETE FROM dossiers WHERE id = :i"), {"i": archive.id}
                )
                await jetable.commit()

    message = str(exc.value).lower()
    assert "archive" in message or "conservation" in message, (
        f"Le refus doit être motivé par la conservation décennale — reçu : {message[:200]}"
    )

    # Le dossier est toujours là — la suppression n'a pas eu lieu.
    with _scope_of(db):
        restant = (await db.execute(
            text("SELECT count(*) FROM dossiers WHERE id = :i"), {"i": archive.id}
        )).scalar_one()
    assert restant == 1, "Art. 23 violé : un dossier archivé a pu être supprimé."


async def test_55_dossier_non_archive_reste_supprimable(db):
    """Contrôle inverse : le verrou ne doit mordre que sur l'état « archivé »."""
    from sqlalchemy import text

    from tests.conftest import _scope_of

    utilisateur = await _acteur(db, "admin")
    brouillon = await create_dossier(db, created_by=utilisateur.id, statut="brouillon")

    with _scope_of(db):
        await db.execute(text("DELETE FROM dossiers WHERE id = :i"), {"i": brouillon.id})
        await db.commit()
        restant = (await db.execute(
            text("SELECT count(*) FROM dossiers WHERE id = :i"), {"i": brouillon.id}
        )).scalar_one()
    assert restant == 0
