"""Recette de conformité au cahier des charges — Modules 4, 5 et 6.

Périmètre couvert :

* **Module 4 — Workflow Dossier** (CDC §4.1/§4.2) : les 8 états, la matrice de
  transitions, la clôture réservée (WRK-04), le déclenchement automatique de
  l'archivage (§5.2, Art. 23), l'immuabilité de l'état « Archivé », l'assignation
  (WRK-05), les commentaires internes horodatés (WRK-06) et l'historique complet
  des changements d'état.
* **Module 5 — Registres & Traçabilité** (CDC §5.1/§5.3) : présence des 5
  registres obligatoires, contenu du registre des dossiers à risque élevé
  (score ≥ 14/20), exports PDF/Excel, confidentialité du registre des DOS
  (Art. 63) et cloisonnement REG-01/REG-02 vis-à-vis des clercs.
* **Module 6 — Reporting** (CDC §6.1/§6.2) : restriction P³ du tableau de bord
  des clercs, absence de toute donnée DOS dans leur périmètre (DOS-04, Art. 63),
  et droits de génération/export des rapports RPT-01/02/03.

Les tests sont rejouables : chaque cas provisionne ses propres utilisateurs et
dossiers (identifiants aléatoires) et n'affirme jamais rien sur le volume global
du cabinet de test, que les autres fichiers de la suite alimentent aussi.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import select, text

from app.core.archivage import DUREE_CONSERVATION_ANNEES, date_expiration_conservation
from app.core.database import tenant_session
from app.core.tenant_context import tenant_scope
from app.models.dossier import Dossier
from tests.conftest import auth_headers, create_dossier, create_user

pytestmark = pytest.mark.asyncio(loop_scope="session")


# Les 8 états du CDC §4.1, dans l'ordre du cycle de vie décrit par le document.
ETATS_CDC = [
    "brouillon", "en_analyse", "vigilance_renforcee", "valide",
    "bloque", "traite", "cloture", "archive",
]

# Les 5 registres obligatoires du CDC §5.1.
REGISTRES_OBLIGATOIRES = ["kyc", "alertes", "risque_eleve", "dos", "journal"]

# Rôles applicatifs de la matrice de permissions (CDC §7.3).
TOUS_LES_ROLES = ["admin", "notaire_principal", "responsable_conformite", "clercs"]

# Signatures binaires : un export « qui répond 200 » sans être un vrai fichier
# n'est pas exploitable par un contrôleur. On vérifie le format, pas juste le code.
MAGIC_PDF = b"%PDF"
MAGIC_ZIP = b"PK\x03\x04"  # un .xlsx est une archive ZIP OOXML


async def _creer_roles(db):
    """Un utilisateur par rôle applicatif, propre au test appelant."""
    return {role: await create_user(db, role=role) for role in TOUS_LES_ROLES}


async def _statut_en_base(db, dossier_id: str) -> Dossier:
    """Relit un dossier depuis la base, pour observer l'état réellement persisté.

    Les mutations passent par l'API, donc par une AUTRE session que celle des
    fixtures : sans rechargement forcé, l'identity map de `db` resservirait la
    version d'avant l'appel et le test validerait un état périmé.

    `populate_existing` recharge cette seule entité. Un `expire_all()` serait plus
    court mais invaliderait aussi les objets `User` des fixtures : le premier accès
    suivant à `user.id` déclencherait un rafraîchissement paresseux hors contexte
    asynchrone, et donc un `MissingGreenlet` sans rapport avec ce qu'on teste.
    """
    with tenant_scope(db.info.get("tenant")):
        result = await db.execute(
            select(Dossier)
            .where(Dossier.id == dossier_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()


# ══════════════════════════════════════════════════════════════════════════════
# Module 4 — Workflow Dossier (CDC §4.1 et §4.2)
# ══════════════════════════════════════════════════════════════════════════════


async def test_les_huit_etats_du_cdc_sont_supportes(db, tenant_a):
    """CDC §4.1 — le dossier connaît exactement les 8 états du cahier des charges.

    Vérifié au niveau de l'énumération PostgreSQL et non d'une constante Python :
    c'est le SGBD qui arbitre en dernier ressort ce qu'un dossier peut valoir.
    """
    async with tenant_session(tenant_a) as session:
        # Le type est qualifié par le schéma du cabinet : chaque tenant possède sa
        # propre énumération, et une requête non qualifiée agrégerait celles de
        # tous les cabinets de test présents en base.
        valeurs = (await session.execute(text(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON t.oid = e.enumtypid "
            "JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE t.typname = 'statut_dossier_enum' AND n.nspname = :schema"
        ), {"schema": tenant_a.schema})).scalars().all()
    assert set(valeurs) == set(ETATS_CDC), (
        f"L'énumération des statuts diverge du CDC §4.1 : {sorted(valeurs)}"
    )


async def test_soumission_en_analyse_ouverte_a_tous_les_roles(client, db, tenant_a):
    """WRK-01 « Soumettre un dossier en analyse » — Admin O / Notaire O / RC O / Clercs O."""
    roles = await _creer_roles(db)
    for role, user in roles.items():
        dossier = await create_dossier(db, created_by=user.id, statut="brouillon", assigned_to=user.id)
        r = await client.patch(
            f"/api/dossiers/{dossier.id}/statut",
            params={"new_statut": "en_analyse"},
            headers=auth_headers(user, tenant_a),
        )
        assert r.status_code == 200, f"WRK-01 refusé au rôle {role} : {r.status_code} {r.text}"
        assert r.json()["statut"] == "en_analyse"


@pytest.mark.parametrize(
    "depart,cible",
    [
        # Sauter l'analyse reviendrait à valider une relation d'affaires sans
        # examen du risque : interdit par la logique même des Art. 16-17.
        ("brouillon", "valide"),
        ("brouillon", "cloture"),
        # Archiver sans clôturer priverait la conservation de son point de départ
        # (Art. 23 : « à compter de la date de clôture »).
        ("en_analyse", "archive"),
        ("valide", "archive"),
        # Rétrograder un dossier validé en brouillon effacerait la traçabilité de
        # la décision de validation.
        ("valide", "brouillon"),
        ("traite", "en_analyse"),
    ],
)
async def test_transitions_interdites_sont_refusees(client, db, tenant_a, depart, cible):
    """CDC §4.1 — le graphe de transitions n'autorise pas les raccourcis de workflow."""
    admin = await create_user(db, role="admin")
    dossier = await create_dossier(db, created_by=admin.id, statut=depart, assigned_to=admin.id)
    r = await client.patch(
        f"/api/dossiers/{dossier.id}/statut",
        params={"new_statut": cible, "commentaire": "Tentative de transition hors graphe."},
        headers=auth_headers(admin, tenant_a),
    )
    assert r.status_code == 422, (
        f"La transition '{depart}' → '{cible}' devrait être refusée, reçu {r.status_code}."
    )
    assert (await _statut_en_base(db, dossier.id)).statut == depart


async def test_cloture_reservee_au_notaire_principal_et_a_l_admin(client, db, tenant_a):
    """WRK-04 « Clôturer un dossier » — Admin O / Notaire Principal O / RC N / Clercs N.

    Séparation des fonctions (Art. 12) : celui qui analyse le risque n'est pas
    celui qui prononce la fin de la relation d'affaires.
    """
    roles = await _creer_roles(db)

    for role in ("responsable_conformite", "clercs"):
        user = roles[role]
        dossier = await create_dossier(db, created_by=user.id, statut="traite", assigned_to=user.id)
        r = await client.patch(
            f"/api/dossiers/{dossier.id}/statut",
            params={"new_statut": "cloture", "commentaire": "Clôture demandée."},
            headers=auth_headers(user, tenant_a),
        )
        assert r.status_code == 403, f"WRK-04 : le rôle {role} ne doit pas pouvoir clôturer."

    for role in ("notaire_principal", "admin"):
        user = roles[role]
        dossier = await create_dossier(db, created_by=user.id, statut="traite", assigned_to=user.id)
        r = await client.patch(
            f"/api/dossiers/{dossier.id}/statut",
            params={"new_statut": "cloture", "commentaire": "Relation d'affaires terminée."},
            headers=auth_headers(user, tenant_a),
        )
        assert r.status_code == 200, f"WRK-04 : le rôle {role} doit pouvoir clôturer ({r.text})."


async def test_cloture_declenche_automatiquement_l_archivage_dix_ans(client, db, tenant_a):
    """CDC §5.2 / Art. 23 — « Le passage en état Clôturé déclenche automatiquement l'archivage ».

    La conservation court « à compter de la date de clôture » : le dossier doit
    donc porter, dès sa clôture, sa date d'archivage et l'échéance des 10 ans.
    Sans cet ancrage, le cabinet ne peut ni justifier la durée de conservation
    devant un contrôle, ni déclencher l'alerte d'expiration J-180 prévue au CDC.
    """
    notaire = await create_user(db, role="notaire_principal")
    dossier = await create_dossier(db, created_by=notaire.id, statut="traite", assigned_to=notaire.id)

    # Avant clôture : aucune échéance de conservation n'a de raison d'exister.
    avant = await _statut_en_base(db, dossier.id)
    assert avant.archivage_date is None
    assert avant.archivage_expiration is None

    r = await client.patch(
        f"/api/dossiers/{dossier.id}/statut",
        params={"new_statut": "cloture", "commentaire": "Acte signé — relation terminée."},
        headers=auth_headers(notaire, tenant_a),
    )
    assert r.status_code == 200, r.text

    apres = await _statut_en_base(db, dossier.id)
    assert apres.statut == "cloture"
    assert apres.archivage_date is not None, (
        "Art. 23 : la clôture doit déclencher l'archivage — aucune date d'archivage posée."
    )
    assert apres.archivage_date == date.today()
    assert apres.archivage_expiration == date_expiration_conservation(apres.archivage_date)
    assert apres.archivage_expiration.year - apres.archivage_date.year == DUREE_CONSERVATION_ANNEES

    # L'échéance doit être opposable, donc exposée par l'API (Art. 103 — communication CENTIF).
    payload = r.json()
    assert payload["archivage_date"] == apres.archivage_date.isoformat()
    assert payload["archivage_expiration"] == apres.archivage_expiration.isoformat()


async def test_archivage_ne_repousse_pas_l_echeance_si_rejoue(db):
    """Art. 23 — l'échéance des 10 ans est ancrée une fois pour toutes.

    Un archivage idempotent évite qu'une opération rejouée ne prolonge
    arbitrairement la conservation d'un dossier déjà archivé.
    """
    from app.core import archivage

    class _Faux:
        archivage_date = date(2020, 1, 15)
        archivage_expiration = date(2030, 1, 15)

    faux = _Faux()
    archivage.declencher_archivage(faux)
    assert faux.archivage_date == date(2020, 1, 15)
    assert faux.archivage_expiration == date(2030, 1, 15)


async def test_29_fevrier_ne_casse_pas_le_calcul_des_dix_ans():
    """Art. 23 — clôturer un 29 février ne doit pas faire échouer l'archivage.

    2020 + 10 = 2030, qui n'est pas bissextile : un `replace(year=…)` naïf lèverait
    une ValueError au moment exact de la clôture, c'est-à-dire un défaut d'archivage.
    """
    assert date_expiration_conservation(date(2020, 2, 29)) == date(2030, 2, 28)


@pytest.mark.parametrize("role", TOUS_LES_ROLES)
async def test_dossier_archive_est_en_lecture_seule_pour_chaque_role(client, db, tenant_a, role):
    """CDC §5.2 — état Archivé : « Lecture seule — Aucune modification possible par aucun rôle ».

    L'interdiction est absolue : elle ne souffre aucune exception, pas même pour
    l'Administrateur. On éprouve les quatre surfaces d'écriture d'un dossier
    (transaction, assignation, commentaire interne, données KYC) pour chaque rôle.
    """
    user = await create_user(db, role=role)
    dossier = await create_dossier(db, created_by=user.id, statut="archive", assigned_to=user.id)
    headers = auth_headers(user, tenant_a)

    ecritures = [
        ("transaction", client.patch(
            f"/api/dossiers/{dossier.id}/transaction",
            json={"montant_tranche": "plus_15m", "mode_paiement": "especes"},
            headers=headers,
        )),
        ("commentaire interne", client.post(
            f"/api/dossiers/{dossier.id}/commentaires",
            json={"contenu": "Tentative d'ajout sur dossier archivé."},
            headers=headers,
        )),
        ("assignation", client.patch(
            f"/api/dossiers/{dossier.id}/assign",
            params={"user_id": user.id},
            headers=headers,
        )),
        ("KYC personne physique", client.put(
            f"/api/dossiers/{dossier.id}/kyc/pp",
            json={"nom": "MODIFIE", "prenoms": "Tentative"},
            headers=headers,
        )),
    ]
    for libelle, requete in ecritures:
        r = await requete
        assert r.status_code == 403, (
            f"Art. 23 : le rôle {role} a pu écrire sur un dossier archivé "
            f"via « {libelle} » (HTTP {r.status_code})."
        )

    # La consultation, elle, reste ouverte : c'est l'objet même de la conservation.
    r = await client.get(f"/api/dossiers/{dossier.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["statut"] == "archive"


@pytest.mark.parametrize("cible", ["en_analyse", "valide", "bloque", "cloture", "traite"])
async def test_aucune_sortie_de_l_etat_archive(client, db, tenant_a, cible):
    """CDC §4.1 — « Archivé » est terminal : le dossier n'en ressort pour aucun statut."""
    admin = await create_user(db, role="admin")
    dossier = await create_dossier(db, created_by=admin.id, statut="archive", assigned_to=admin.id)
    r = await client.patch(
        f"/api/dossiers/{dossier.id}/statut",
        params={"new_statut": cible, "commentaire": "Tentative de désarchivage."},
        headers=auth_headers(admin, tenant_a),
    )
    assert r.status_code == 422, f"Un dossier archivé ne doit pas pouvoir repasser en '{cible}'."
    assert (await _statut_en_base(db, dossier.id)).statut == "archive"


async def test_suppression_physique_d_un_dossier_archive_bloquee_par_le_sgbd(db, tenant_a):
    """Art. 23 / Art. 197 — la suppression est bloquée AU NIVEAU BASE DE DONNÉES.

    Le CDC §5.2 exige que le verrou tienne « au niveau base de données » : la
    destruction intentionnelle d'un dossier est une infraction pénale (Art. 197),
    la garantie ne peut donc pas reposer sur l'applicatif, qu'un accès SQL direct
    contournerait. On émet donc un DELETE brut, sans passer par l'API.
    """
    admin = await create_user(db, role="admin")
    dossier = await create_dossier(db, created_by=admin.id, statut="archive", assigned_to=admin.id)

    # Session dédiée : l'exception invalide la transaction, on ne pollue pas `db`.
    async with tenant_session(tenant_a) as session:
        with pytest.raises(Exception) as exc:
            await session.execute(text("DELETE FROM dossiers WHERE id = :id"), {"id": dossier.id})
            await session.commit()
        assert "archiv" in str(exc.value).lower(), (
            f"Le trigger `prevent_archive_delete` n'a pas produit l'erreur attendue : {exc.value}"
        )
        await session.rollback()

    # Contrôle décisif : le dossier est toujours là.
    assert (await _statut_en_base(db, dossier.id)).statut == "archive"


async def test_suppression_autorisee_sur_un_dossier_non_archive(db, tenant_a):
    """Contre-épreuve : le trigger vise l'état « Archivé », pas tous les dossiers.

    Sans ce test, un trigger qui interdirait TOUTE suppression passerait le test
    précédent tout en étant faux.
    """
    admin = await create_user(db, role="admin")
    dossier = await create_dossier(db, created_by=admin.id, statut="brouillon", assigned_to=admin.id)
    async with tenant_session(tenant_a) as session:
        await session.execute(text("DELETE FROM dossiers WHERE id = :id"), {"id": dossier.id})
        await session.commit()
        reste = (await session.execute(
            text("SELECT count(*) FROM dossiers WHERE id = :id"), {"id": dossier.id}
        )).scalar_one()
    assert reste == 0


async def test_assignation_de_dossier_et_journalisation(client, db, tenant_a):
    """CDC §4.2 — « Assignation de dossiers à un utilisateur spécifique » (WRK-05)."""
    admin = await create_user(db, role="admin")
    clerc = await create_user(db, role="clercs")
    dossier = await create_dossier(db, created_by=admin.id, statut="en_analyse")

    r = await client.patch(
        f"/api/dossiers/{dossier.id}/assign",
        params={"user_id": clerc.id},
        headers=auth_headers(admin, tenant_a),
    )
    assert r.status_code == 200, r.text
    assert (await _statut_en_base(db, dossier.id)).assigned_to == clerc.id

    # L'assigné voit désormais son dossier ; c'est le pendant de P¹ (KYC-05).
    r = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 200


async def test_un_clerc_ne_voit_pas_les_dossiers_non_assignes(client, db, tenant_a):
    """P¹ (CDC §7.3) — « Clercs : consultation limitée aux dossiers qui leur sont assignés »."""
    rc = await create_user(db, role="responsable_conformite")
    clerc = await create_user(db, role="clercs")
    dossier = await create_dossier(db, created_by=rc.id, statut="en_analyse", assigned_to=rc.id)

    r = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 403

    listing = await client.get("/api/dossiers", headers=auth_headers(clerc, tenant_a))
    assert listing.status_code == 200
    assert dossier.reference not in listing.text


async def test_commentaires_internes_horodates_et_confidentiels(client, db, tenant_a):
    """CDC §4.2 — « Commentaires internes horodatés par utilisateur (confidentiels) » (WRK-06).

    Trois exigences distinctes : l'horodatage, l'attribution à un auteur, et la
    confidentialité — un commentaire interne n'est pas lisible par un utilisateur
    étranger au dossier.
    """
    rc = await create_user(db, role="responsable_conformite")
    clerc_assigne = await create_user(db, role="clercs")
    clerc_tiers = await create_user(db, role="clercs")
    dossier = await create_dossier(db, created_by=rc.id, statut="en_analyse", assigned_to=clerc_assigne.id)

    # WRK-06 est ouvert à tous les rôles, clercs compris.
    for auteur in (rc, clerc_assigne):
        r = await client.post(
            f"/api/dossiers/{dossier.id}/commentaires",
            json={"contenu": f"Note interne de {auteur.role} — {uuid.uuid4().hex[:6]}"},
            headers=auth_headers(auteur, tenant_a),
        )
        assert r.status_code == 201, f"WRK-06 refusé au rôle {auteur.role} : {r.text}"

    r = await client.get(f"/api/dossiers/{dossier.id}/commentaires", headers=auth_headers(rc, tenant_a))
    assert r.status_code == 200
    commentaires = r.json()
    assert len(commentaires) == 2

    for c in commentaires:
        assert c["created_at"], "Un commentaire interne doit être horodaté (CDC §4.2)."
        assert c["user_id"], "Un commentaire interne doit être attribué à son auteur (CDC §4.2)."
    auteurs = {c["user_id"] for c in commentaires}
    assert auteurs == {rc.id, clerc_assigne.id}
    # Ordre chronologique : l'historique se lit dans le sens de la vie du dossier.
    assert [c["created_at"] for c in commentaires] == sorted(c["created_at"] for c in commentaires)

    # Confidentialité : un clerc étranger au dossier n'y accède ni en lecture ni en écriture.
    r = await client.get(
        f"/api/dossiers/{dossier.id}/commentaires", headers=auth_headers(clerc_tiers, tenant_a)
    )
    assert r.status_code == 403
    r = await client.post(
        f"/api/dossiers/{dossier.id}/commentaires",
        json={"contenu": "Intrusion."},
        headers=auth_headers(clerc_tiers, tenant_a),
    )
    assert r.status_code == 403


async def test_historique_complet_des_changements_d_etat(client, db, tenant_a):
    """CDC §4.2 — « Historique complet des changements d'état ».

    On déroule un cycle de vie réel (brouillon → … → clôturé) et on vérifie que
    CHAQUE transition laisse une trace attribuée et motivée : c'est la pièce qui
    rend le dossier auditable au sens de l'Art. 23.
    """
    notaire = await create_user(db, role="notaire_principal")
    headers = auth_headers(notaire, tenant_a)
    dossier = await create_dossier(db, created_by=notaire.id, statut="brouillon", assigned_to=notaire.id)

    parcours = [
        ("en_analyse", None),
        ("valide", "Diligences complètes — relation autorisée."),
        ("traite", "Acte instrumenté."),
        ("cloture", "Relation d'affaires terminée."),
    ]
    for cible, commentaire in parcours:
        params = {"new_statut": cible}
        if commentaire:
            params["commentaire"] = commentaire
        r = await client.patch(f"/api/dossiers/{dossier.id}/statut", params=params, headers=headers)
        assert r.status_code == 200, f"Transition vers '{cible}' refusée : {r.text}"

    r = await client.get(f"/api/dossiers/{dossier.id}/historique", headers=headers)
    assert r.status_code == 200
    historique = r.json()
    assert len(historique) == len(parcours), (
        f"L'historique doit contenir les {len(parcours)} changements d'état, reçu {len(historique)}."
    )

    actions = [h["action"] for h in historique]
    assert actions == [
        "brouillon → en_analyse",
        "en_analyse → valide",
        "valide → traite",
        "traite → cloture",
    ]
    for entree in historique:
        assert entree["user_id"] == notaire.id, "Chaque changement d'état doit être attribué."
        assert entree["created_at"], "Chaque changement d'état doit être horodaté (UTC)."
    # Le commentaire de motivation est conservé pour les transitions qui l'exigent.
    assert historique[-1]["detail"]["commentaire"] == "Relation d'affaires terminée."


async def test_commentaire_obligatoire_sur_les_transitions_engageantes(client, db, tenant_a):
    """CDC §4.2 — la traçabilité impose de motiver les décisions de workflow.

    Seule la soumission initiale (brouillon → en analyse) en est dispensée : elle
    ne tranche rien, elle transmet.
    """
    rc = await create_user(db, role="responsable_conformite")
    dossier = await create_dossier(db, created_by=rc.id, statut="en_analyse", assigned_to=rc.id)
    r = await client.patch(
        f"/api/dossiers/{dossier.id}/statut",
        params={"new_statut": "vigilance_renforcee"},
        headers=auth_headers(rc, tenant_a),
    )
    assert r.status_code == 422
    assert "commentaire" in r.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Module 5 — Registres & Traçabilité (CDC §5.1 et §5.3)
# ══════════════════════════════════════════════════════════════════════════════


async def test_les_cinq_registres_obligatoires_sont_exposes(client, db, tenant_a):
    """CDC §5.1 — Registre KYC, Registre des alertes, Registre des dossiers à risque
    élevé, Registre des DOS et Journal des actions."""
    admin = await create_user(db, role="admin")
    r = await client.get("/api/registres", headers=auth_headers(admin, tenant_a))
    assert r.status_code == 200
    exposes = {reg["id"] for reg in r.json()["registres"]}
    manquants = set(REGISTRES_OBLIGATOIRES) - exposes
    assert not manquants, f"Registres obligatoires absents du CDC §5.1 : {sorted(manquants)}"


async def test_registre_des_dossiers_a_risque_eleve_contient_les_scores_superieurs_a_14(
    client, db, tenant_a
):
    """CDC §5.1 — « Registre des dossiers à risque élevé : dossiers avec score ≥ 14/20 ».

    Le seuil de 14 est celui de la classification ÉLEVÉ (CDC §2.2, verrouillé) : un
    dossier qui l'atteint doit figurer au registre, un dossier en deçà ne le doit pas.
    """
    rc = await create_user(db, role="responsable_conformite")
    eleve = await create_dossier(
        db, created_by=rc.id, statut="en_analyse", score_base=15, classification="ELEVE",
    )
    limite = await create_dossier(
        db, created_by=rc.id, statut="en_analyse", score_base=14, classification="ELEVE",
    )
    faible = await create_dossier(
        db, created_by=rc.id, statut="en_analyse", score_base=5, classification="FAIBLE",
    )

    r = await client.get(
        "/api/registres/risque_eleve",
        params={"limit": 500},
        headers=auth_headers(rc, tenant_a),
    )
    assert r.status_code == 200, r.text
    corps = r.json()
    references = {item["reference"] for item in corps["items"]}

    assert eleve.reference in references, "Un dossier à 15/20 doit figurer au registre risque élevé."
    assert limite.reference in references, "Le seuil de 14/20 est inclusif (CDC §2.2)."
    assert faible.reference not in references, (
        "Un dossier à 5/20 (FAIBLE) n'a rien à faire au registre des dossiers à risque élevé."
    )
    # Le registre doit être exploitable : score et classification y figurent.
    ligne = next(i for i in corps["items"] if i["reference"] == eleve.reference)
    assert ligne["score_base"] == 15
    assert ligne["classification"] == "ELEVE"


async def test_registre_risque_eleve_inclut_les_dossiers_forces_par_trigger(client, db, tenant_a):
    """CDC §2.3 — un trigger absolutoire classe ÉLEVÉ « indépendamment du score de base ».

    Un dossier PPE à 8/20 (T1) est un dossier à risque élevé au sens réglementaire :
    l'exclure du registre parce que son score brut est inférieur à 14 masquerait
    précisément les dossiers les plus sensibles.
    """
    rc = await create_user(db, role="responsable_conformite")
    ppe = await create_dossier(
        db, created_by=rc.id, statut="en_analyse",
        score_base=8, classification="ELEVE", trigger_actif="T1", force_par_trigger=True,
    )
    r = await client.get(
        "/api/registres/risque_eleve", params={"limit": 500}, headers=auth_headers(rc, tenant_a)
    )
    assert r.status_code == 200
    ligne = next((i for i in r.json()["items"] if i["reference"] == ppe.reference), None)
    assert ligne is not None, "Un dossier classé ÉLEVÉ par trigger T1 doit figurer au registre."
    assert ligne["trigger_actif"] == "T1"


@pytest.mark.parametrize("registre", REGISTRES_OBLIGATOIRES)
@pytest.mark.parametrize("format_export", ["pdf", "excel"])
async def test_export_des_registres_produit_un_fichier_exploitable(
    client, db, tenant_a, registre, format_export
):
    """CDC §5.3 — « Export PDF/Excel des registres » (REG-02).

    Un export de conformité doit être un fichier réel : on vérifie le type MIME,
    la signature binaire et le fait qu'il ne soit pas vide. Un 200 renvoyant zéro
    octet serait inexploitable devant une autorité de contrôle (Art. 103).
    """
    admin = await create_user(db, role="admin")
    r = await client.get(
        f"/api/registres/{registre}/export",
        params={"format": format_export},
        headers=auth_headers(admin, tenant_a),
    )
    assert r.status_code == 200, f"Export {registre}/{format_export} en échec : {r.text[:300]}"
    assert len(r.content) > 0, "Un export de registre ne doit jamais être vide."

    if format_export == "pdf":
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content.startswith(MAGIC_PDF), "Le contenu n'est pas un PDF valide."
    else:
        assert "spreadsheetml" in r.headers["content-type"]
        assert r.content.startswith(MAGIC_ZIP), "Le contenu n'est pas un classeur XLSX valide."
    assert "attachment" in r.headers.get("content-disposition", "")


@pytest.mark.parametrize("role", ["admin", "notaire_principal", "responsable_conformite"])
async def test_registre_dos_accessible_aux_roles_habilites(client, db, tenant_a, role):
    """Art. 63 / CDC §8.5 — le registre des DOS est ouvert au RC, au Notaire Principal
    et à l'Administrateur, et à eux seuls."""
    user = await create_user(db, role=role)
    r = await client.get("/api/registres/dos", headers=auth_headers(user, tenant_a))
    assert r.status_code == 200, f"Le rôle {role} doit accéder au registre des DOS : {r.text}"


async def test_registre_dos_ferme_aux_clercs(client, db, tenant_a):
    """Art. 63 — « Le statut DOS en cours est visible uniquement par Responsable
    conformité, Notaire principal et Administrateur » ; DOS-04 : Clercs = N.

    La confidentialité du DOS est pénalement sanctionnée : le cloisonnement doit
    valoir aussi bien pour la consultation que pour l'export, et le registre ne
    doit même pas apparaître dans la liste servie à un clerc.
    """
    clerc = await create_user(db, role="clercs")
    headers = auth_headers(clerc, tenant_a)

    r = await client.get("/api/registres/dos", headers=headers)
    assert r.status_code == 403, "Art. 63 : un clerc ne doit pas consulter le registre des DOS."

    r = await client.get("/api/registres/dos/export", params={"format": "pdf"}, headers=headers)
    assert r.status_code == 403, "Art. 63 : un clerc ne doit pas exporter le registre des DOS."

    r = await client.get("/api/registres", headers=headers)
    assert r.status_code == 200
    assert "dos" not in {reg["id"] for reg in r.json()["registres"]}


@pytest.mark.parametrize("registre", REGISTRES_OBLIGATOIRES)
async def test_aucun_registre_n_est_accessible_aux_clercs(client, db, tenant_a, registre):
    """REG-01 « Consulter les registres » / REG-02 « Exporter les registres » — Clercs = N.

    Les registres sont des pièces de conformité opposables : leur consultation
    relève de la supervision (Art. 12), pas de la saisie opérationnelle.
    """
    clerc = await create_user(db, role="clercs")
    headers = auth_headers(clerc, tenant_a)

    r = await client.get(f"/api/registres/{registre}", headers=headers)
    assert r.status_code == 403, (
        f"REG-01 : le registre '{registre}' ne doit pas être consultable par un clerc "
        f"(reçu HTTP {r.status_code})."
    )
    r = await client.get(f"/api/registres/{registre}/export", params={"format": "pdf"}, headers=headers)
    assert r.status_code == 403, f"REG-02 : le registre '{registre}' ne doit pas être exportable par un clerc."


async def test_liste_des_registres_vide_pour_un_clerc(client, db, tenant_a):
    """REG-01 — la liste ne doit pas révéler l'existence de registres interdits."""
    clerc = await create_user(db, role="clercs")
    r = await client.get("/api/registres", headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 200
    assert r.json()["registres"] == []


async def test_journal_des_actions_accessible_au_notaire_principal(client, db, tenant_a):
    """CDC §7.3 — le Notaire Principal cumule REG-01 (registres) et ADM-06 (logs).

    Lui refuser le journal des actions de son propre cabinet le priverait du moyen
    d'exercer la supervision que l'Art. 12 met à sa charge.
    """
    notaire = await create_user(db, role="notaire_principal")
    r = await client.get("/api/registres/journal", headers=auth_headers(notaire, tenant_a))
    assert r.status_code == 200, (
        f"Le Notaire Principal doit accéder au journal des actions (reçu {r.status_code})."
    )
    assert r.json()["id"] == "journal"


async def test_journal_des_actions_horodate_et_trace_l_auteur(client, db, tenant_a):
    """CDC §5.3 — « chaque action est enregistrée avec identité de l'auteur,
    horodatage UTC, et adresse IP »."""
    admin = await create_user(db, role="admin")
    headers = auth_headers(admin, tenant_a)

    # On produit une action traçable, puis on la retrouve au journal.
    dossier = await create_dossier(db, created_by=admin.id, statut="brouillon", assigned_to=admin.id)
    r = await client.patch(
        f"/api/dossiers/{dossier.id}/statut",
        params={"new_statut": "en_analyse"},
        headers=headers,
    )
    assert r.status_code == 200

    r = await client.get("/api/registres/journal", params={"limit": 200}, headers=headers)
    assert r.status_code == 200
    trace = next(
        (e for e in r.json()["items"]
         if e["entity_id"] == dossier.id and e["action"] == "dossier.statut_change"),
        None,
    )
    assert trace is not None, "Le changement de statut doit figurer au journal des actions."
    assert trace["timestamp"], "Horodatage UTC obligatoire (CDC §5.3)."
    assert trace["user_id"] == admin.id, "Identité de l'auteur obligatoire (CDC §5.3)."
    assert trace["user_role"] == "admin"
    assert trace["ip"], "Adresse IP obligatoire (CDC §5.3)."


# ══════════════════════════════════════════════════════════════════════════════
# Module 6 — Reporting (CDC §6.1 et §6.2)
# ══════════════════════════════════════════════════════════════════════════════

# Clés du tableau de bord qui portent des statistiques à l'échelle du cabinet.
# P³ les interdit toutes au clerc.
CLES_GLOBALES = [
    "dossiers_by_statut",     # nombre de dossiers KYC par statut, tout le cabinet
    "risque_distribution",    # répartition des risques du cabinet
    "revisions_dues_30j",     # calendrier de réévaluation du cabinet
    "wrk09_en_attente",       # file de validation PPE du cabinet
    "monthly_data",           # séries mensuelles du cabinet
]


async def test_tableau_de_bord_d_un_clerc_limite_a_ses_dossiers_assignes(client, db, tenant_a):
    """P³ (CDC §7.3) — « Clercs : tableau de bord restreint — uniquement leurs
    dossiers assignés, pas les statistiques globales du cabinet » (RPT-01).

    C'est une exigence de cloisonnement, pas de confort d'affichage : le clerc ne
    doit ni compter ni apercevoir l'activité du cabinet hors de son périmètre.
    """
    clerc = await create_user(db, role="clercs")
    rc = await create_user(db, role="responsable_conformite")

    # Deux dossiers pour le clerc, un pour un tiers — dont il ne doit rien savoir.
    a_lui = [
        await create_dossier(db, created_by=clerc.id, statut="en_analyse", assigned_to=clerc.id),
        await create_dossier(db, created_by=clerc.id, statut="brouillon", assigned_to=clerc.id),
    ]
    du_tiers = await create_dossier(
        db, created_by=rc.id, statut="en_analyse", assigned_to=rc.id,
        score_base=18, classification="ELEVE",
    )

    r = await client.get("/api/dashboard/stats", headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 200, r.text
    stats = r.json()

    assert stats["scope"] == "assigne", "Le tableau de bord d'un clerc doit être servi en périmètre restreint."

    # Aucune statistique à l'échelle du cabinet.
    for cle in CLES_GLOBALES:
        assert cle not in stats, (
            f"P³ : la statistique globale « {cle} » ne doit pas être servie à un clerc."
        )

    # Aucune fuite du dossier d'un tiers, sous quelque forme que ce soit.
    assert du_tiers.reference not in r.text, (
        "P³ : le tableau de bord d'un clerc ne doit contenir aucun dossier qui ne lui est pas assigné."
    )
    for d in stats["recent_dossiers"]:
        assert d["reference"] in {x.reference for x in a_lui}, (
            f"Dossier hors périmètre exposé au clerc : {d['reference']}"
        )

    # Ses propres dossiers, eux, sont bien décomptés.
    assert stats["mes_dossiers_by_statut"].get("en_analyse", 0) >= 1
    assert stats["kyc_en_analyse"] >= 1


async def test_tableau_de_bord_d_un_clerc_ne_revele_aucune_donnee_dos(client, db, tenant_a):
    """DOS-04 (Clercs = N) + Art. 63 / CDC §8.5 — aucune information DOS pour un clerc.

    Le compteur de DOS ouvertes était calculé sans filtre de périmètre : un clerc
    lisait, depuis son tableau de bord, le volume déclaratif du cabinet — à la fois
    une statistique globale interdite par P³ et une donnée DOS interdite par DOS-04.
    """
    from app.models.dos import DeclarationSuspicion

    rc = await create_user(db, role="responsable_conformite")
    clerc = await create_user(db, role="clercs")
    dossier_tiers = await create_dossier(db, created_by=rc.id, statut="bloque", assigned_to=rc.id)
    await create_dossier(db, created_by=clerc.id, statut="en_analyse", assigned_to=clerc.id)

    # Une DOS bien réelle, sur un dossier qui n'appartient pas au clerc.
    with tenant_scope(db.info.get("tenant")):
        db.add(DeclarationSuspicion(
            dossier_id=dossier_tiers.id,
            reference_interne=f"DOS-{uuid.uuid4().hex[:10].upper()}",
            statut="brouillon",
            initie_par=rc.id,
        ))
        await db.commit()

    r = await client.get("/api/dashboard/stats", headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 200
    assert r.json()["dos_ouvertes"] == 0, (
        "Art. 63 / DOS-04 : aucun volume de DOS du cabinet ne doit remonter au tableau de bord d'un clerc."
    )

    # Contre-épreuve : le RC, lui, doit bien voir l'activité déclarative.
    r = await client.get("/api/dashboard/stats", headers=auth_headers(rc, tenant_a))
    assert r.status_code == 200
    assert r.json()["dos_ouvertes"] >= 1


@pytest.mark.parametrize("role", ["admin", "notaire_principal", "responsable_conformite"])
async def test_tableau_de_bord_global_pour_les_roles_de_supervision(client, db, tenant_a, role):
    """RPT-01 / CDC §6.1 — Admin, Notaire Principal et RC accèdent aux tableaux de bord
    complets : dossiers par statut, répartition des risques, alertes, réévaluations."""
    user = await create_user(db, role=role)
    await create_dossier(db, created_by=user.id, statut="en_analyse", score_base=16, classification="ELEVE")

    r = await client.get("/api/dashboard/stats", headers=auth_headers(user, tenant_a))
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["scope"] == "global"
    # CDC §6.1 — les indicateurs attendus du tableau de bord de supervision.
    for cle in ("dossiers_by_statut", "risque_distribution", "alertes_ouvertes",
                "revisions_dues_30j", "dossiers_risque_eleve"):
        assert cle in stats, f"Indicateur du CDC §6.1 absent du tableau de bord : {cle}"
    assert stats["risque_distribution"].get("ELEVE", 0) >= 1


@pytest.mark.parametrize(
    "chemin,corps",
    [
        ("/api/rapports/conformite", {}),                       # rapport de conformité périodique
        ("/api/rapports/client", {"dossier_reference": "X"}),   # rapport client
        ("/api/rapports/audit", {}),                            # rapport d'audit
    ],
)
async def test_generation_de_rapports_interdite_aux_clercs(client, db, tenant_a, chemin, corps):
    """RPT-02 « Générer des rapports » et RPT-03 « Exporter des rapports » — Clercs = N.

    Le refus doit intervenir sur le contrôle de rôle, avant toute lecture de
    données : un 403 même sur une référence de dossier inexistante.
    """
    clerc = await create_user(db, role="clercs")
    r = await client.post(chemin, json=corps, headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 403, (
        f"RPT-02/03 : {chemin} ne doit pas être accessible à un clerc (reçu {r.status_code})."
    )


async def test_historique_des_rapports_interdit_aux_clercs(client, db, tenant_a):
    """RPT-02/03 — l'historique des rapports générés est lui aussi hors périmètre clerc."""
    clerc = await create_user(db, role="clercs")
    r = await client.get("/api/rapports/historique", headers=auth_headers(clerc, tenant_a))
    assert r.status_code == 403


@pytest.mark.parametrize("role", ["admin", "notaire_principal", "responsable_conformite"])
async def test_rapport_de_conformite_genere_un_pdf(client, db, tenant_a, role):
    """CDC §6.2 — « Rapport de conformité périodique » (RPT-02/03 : Admin/Notaire/RC = O)."""
    user = await create_user(db, role=role)
    r = await client.post(
        "/api/rapports/conformite",
        json={"date_debut": "2026-01-01", "date_fin": "2026-12-31"},
        headers=auth_headers(user, tenant_a),
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(MAGIC_PDF)
    assert len(r.content) > 500, "Un rapport de conformité vide n'est pas un livrable."


async def test_rapport_client_exportable_par_reference(client, db, tenant_a):
    """CDC §6.2 — « Rapport client (dossier complet exportable) »."""
    rc = await create_user(db, role="responsable_conformite")
    dossier = await create_dossier(
        db, created_by=rc.id, statut="valide", score_base=12, classification="MOYEN",
    )
    r = await client.post(
        "/api/rapports/client",
        json={"dossier_reference": dossier.reference},
        headers=auth_headers(rc, tenant_a),
    )
    assert r.status_code == 200, r.text
    assert r.content.startswith(MAGIC_PDF)
    assert dossier.reference in r.headers.get("content-disposition", "")


async def test_rapport_audit_restitue_la_piste_complete(client, db, tenant_a):
    """CDC §6.2 — « Rapport audit (piste d'audit complète avec tous les événements) »."""
    admin = await create_user(db, role="admin")
    r = await client.post("/api/rapports/audit", json={}, headers=auth_headers(admin, tenant_a))
    assert r.status_code == 200, r.text
    assert r.content.startswith(MAGIC_PDF)


async def test_generation_de_rapport_est_elle_meme_tracee(client, db, tenant_a):
    """CDC §5.3 — « Historisation complète de toutes les actions ».

    Produire un rapport est un acte de conformité : il doit laisser une trace
    dans la piste d'audit, faute de quoi nul ne peut établir qui a extrait quoi.
    """
    admin = await create_user(db, role="admin")
    headers = auth_headers(admin, tenant_a)

    r = await client.post("/api/rapports/audit", json={}, headers=headers)
    assert r.status_code == 200

    r = await client.get("/api/rapports/historique", headers=headers)
    assert r.status_code == 200
    traces = [i for i in r.json()["items"] if i["generated_by"] and i["type_rapport"]]
    assert traces, "La génération d'un rapport doit apparaître dans l'historique (CDC §5.3)."
