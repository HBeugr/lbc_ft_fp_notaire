"""Recette de conformité au cahier des charges — Modules 1, 2 et 3.

Périmètre couvert :
  * Module 1 — Gestion des clients (KYC PP, KYC PM, documents par fiche)
  * Module 2 — Matrice de risque (10 axes, seuils verrouillés, triggers T1–T6)
  * Module 3 — Alertes & vigilance

Ces tests ne vérifient pas « que le code fait ce qu'il fait » : ils vérifient
que le code fait ce que l'**Ordonnance N°2023-875** et le CDC exigent. Chaque
test cite donc l'article ou le code CDC (SCO-02, SCO-03, T1…T6, ALE-03) qui le
fonde, parce qu'une régression sur l'une de ces règles n'est pas un défaut
fonctionnel mais un manquement réglementaire opposable au cabinet.

Le cœur du module 2 est le couple « seuils verrouillés / triggers absolutoires » :
c'est la seule partie de l'application qu'aucun rôle, Administrateur compris, ne
doit pouvoir assouplir (CDC §2.2 et §2.3).
"""
import pytest

# Les cabinets de test sont provisionnés une seule fois pour la session : leurs
# connexions appartiennent à la boucle de session, les tests doivent s'y
# rattacher sous peine de « future attached to a different loop » côté asyncpg.
pytestmark = pytest.mark.asyncio(loop_scope="session")

import uuid
from dataclasses import dataclass

from sqlalchemy import text

from app.core import runtime_config
from app.core.tenant_context import tenant_scope
from app.services import scoring_service
from tests.conftest import auth_headers, create_dossier, create_user


# ── Outils communs ───────────────────────────────────────────────────────────

# Seuil légal Art. 72 : au-delà, une opération en espèces déclenche T2.
SEUIL_ESPECES_ART_72 = 15_000_000

# Jeu d'axes neutre : les 10 axes à 0, soit un score de base de 0/20 (FAIBLE).
# Sert à prouver qu'un trigger absolutoire s'impose même sur un dossier
# parfaitement anodin.
AXES_NULS = {code: 0 for code in scoring_service.AXIS_CODES}


def axes_totalisant(total: int) -> dict[str, int]:
    """Répartit `total` points sur les 10 axes, chacun plafonné à 2 (CDC §2.1).

    Permet de viser un score de base exact et donc d'éprouver les BORNES des
    seuils de classification, seul endroit où une erreur d'inégalité (`<` au
    lieu de `<=`) se voit.
    """
    assert 0 <= total <= 20, "le score de base est borné à 20 (10 axes × 2 points)"
    axes = {}
    restant = total
    for code in scoring_service.AXIS_CODES:
        pris = min(2, restant)
        axes[code] = pris
        restant -= pris
    assert restant == 0
    return axes


@pytest.fixture
async def config_scoring_restauree(db, tenant_a):
    """Restaure pondérations et seuil espèces après un test qui les modifie.

    La configuration de scoring est mise en cache par cabinet pour toute la
    durée du processus : sans restauration, un test qui double une pondération
    fausserait silencieusement tous les suivants et la suite ne serait pas
    rejouable.
    """
    with tenant_scope(tenant_a):
        poids_initiaux = runtime_config.get_ponderations()
        seuil_initial = runtime_config.get_seuil_especes_t2()
    yield
    with tenant_scope(tenant_a):
        await runtime_config.set_ponderations(db, poids_initiaux)
        await runtime_config.set_seuil_especes_t2(db, seuil_initial)
        await db.commit()


@dataclass(frozen=True)
class _Compte:
    """Identité minimale d'un compte de test (ce dont `auth_headers` a besoin).

    On ne conserve pas l'instance ORM : la session de test est refermée entre
    deux tests, et lire un attribut d'un objet détaché lèverait une erreur.
    """

    id: str
    role: str


# Comptes mutualisés par rôle, créés une seule fois pour le module.
#
# Ce n'est pas qu'une optimisation. Les cabinets de test sont provisionnés pour
# TOUTE la session et partagés par tous les fichiers de recette : un compte créé
# par test ferait grossir l'annuaire du cabinet de plusieurs dizaines d'entrées,
# au point de faire déborder la première page de `GET /api/users` et de mettre
# en échec des tests d'un autre fichier. Aucun test de ce module n'a besoin d'un
# utilisateur neuf — seul son RÔLE importe.
_comptes: dict[str, _Compte] = {}


async def utilisateur(db, role: str) -> _Compte:
    """Compte mutualisé du rôle demandé, créé à la première utilisation."""
    compte = _comptes.get(role)
    if compte is None:
        cree = await create_user(db, role=role)
        compte = _Compte(id=cree.id, role=cree.role)
        _comptes[role] = compte
    return compte


async def _dossier_pour(client, db, role: str = "responsable_conformite", **kwargs):
    """Compte du rôle demandé et dossier neuf qui lui est assigné.

    Le dossier, lui, est toujours neuf : c'est l'objet sous test (score, statut,
    alertes), et le réutiliser rendrait les tests dépendants de leur ordre.
    """
    user = await utilisateur(db, role)
    dossier = await create_dossier(db, created_by=user.id, assigned_to=user.id, **kwargs)
    return user, dossier


async def _calculer(client, user, dossier_id: str, **payload):
    """Appelle POST /scoring/calculate et renvoie la réponse brute."""
    corps = {"axes": AXES_NULS, **payload}
    return await client.post(
        f"/api/dossiers/{dossier_id}/scoring/calculate",
        json=corps,
        headers=auth_headers(user),
    )


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 2 — Seuils de classification (CDC §2.2 — « verrouillés »)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("score", "classification_attendue"),
    [
        (0, "FAIBLE"),
        (7, "FAIBLE"),   # borne haute FAIBLE
        (8, "MOYEN"),    # borne basse MOYEN
        (13, "MOYEN"),   # borne haute MOYEN
        (14, "ELEVE"),   # borne basse ÉLEVÉ
        (20, "ELEVE"),
    ],
)
async def test_seuils_de_classification_aux_bornes_exactes(score, classification_attendue):
    """CDC §2.2 : 0-7 FAIBLE, 8-13 MOYEN, 14-20 ÉLEVÉ.

    Les bornes sont testées une par une : c'est la seule façon de détecter une
    inégalité stricte mal placée, qui ferait par exemple basculer un dossier à 14
    en MOYEN et priverait le cabinet de la vigilance renforcée exigée à ce niveau.
    """
    resultat = scoring_service.calculate(axes_totalisant(score))
    assert resultat.score == score
    assert resultat.classification == classification_attendue


async def test_seuils_aux_bornes_via_api(client, db):
    """Les bornes CDC §2.2 valent aussi de bout en bout, via l'API.

    Un seuil correct dans le service mais mal restitué par l'endpoint reviendrait
    au même pour l'utilisateur : c'est la classification affichée qui déclenche
    (ou non) la vigilance renforcée.
    """
    user, dossier = await _dossier_pour(client, db)
    for score, attendu in ((7, "FAIBLE"), (8, "MOYEN"), (13, "MOYEN"), (14, "ELEVE")):
        reponse = await client.post(
            f"/api/dossiers/{dossier.id}/scoring/calculate",
            json={"axes": axes_totalisant(score)},
            headers=auth_headers(user),
        )
        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["total"] == score
        assert corps["niveau"] == attendu, f"score {score} → {corps['niveau']} au lieu de {attendu}"


async def test_seuils_non_modifiables_meme_par_admin(client, db):
    """SCO-03 = N pour TOUS les rôles, Administrateur compris (CDC §2.2, §7.3).

    On tente d'injecter des seuils par la seule surface d'écriture du scoring
    (`PUT /api/scoring/weights`, réservée à l'Admin). Deux garanties sont
    attendues : la configuration exposée ne contient aucun seuil de
    classification, et le comportement de classification reste inchangé.
    """
    admin = await utilisateur(db, "admin")

    reponse = await client.put(
        "/api/scoring/weights",
        json={
            "weights": {
                # Tentative d'injection de seuils sous couvert de pondérations.
                "seuil_faible_max": 20,
                "seuil_moyen_max": 20,
                "seuil_eleve_min": 99,
            }
        },
        headers=auth_headers(admin),
    )
    assert reponse.status_code == 200, reponse.text
    config = reponse.json()
    for cle in ("seuil_faible_max", "seuil_moyen_max", "seuil_eleve_min"):
        assert cle not in config, f"le seuil « {cle} » ne doit jamais être paramétrable (SCO-03)"

    # La classification reste celle du CDC après la tentative.
    assert scoring_service.calculate(axes_totalisant(7)).classification == "FAIBLE"
    assert scoring_service.calculate(axes_totalisant(14)).classification == "ELEVE"


async def test_aucun_endpoint_n_expose_les_seuils_de_classification():
    """SCO-03 : aucune route de l'API ne doit accepter un seuil de classification.

    Contrôle structurel : on inspecte le schéma OpenAPI plutôt qu'un endpoint
    connu, de sorte qu'une future route « paramétrage des seuils » soit détectée
    dès son ajout, sans avoir à penser à écrire le test correspondant.
    """
    from app.main import app

    schema = app.openapi()
    interdits = ("seuil_faible", "seuil_moyen", "seuil_eleve", "seuil_classification")
    fautifs = []
    for nom, definition in (schema.get("components", {}).get("schemas") or {}).items():
        for propriete in (definition.get("properties") or {}):
            if any(mot in propriete.lower() for mot in interdits):
                fautifs.append(f"{nom}.{propriete}")
    assert not fautifs, f"seuils de classification exposés à l'écriture (SCO-03) : {fautifs}"


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 2 — Pondérations des axes (CDC §7.2, SCO-02 : Admin uniquement)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("role", ["notaire_principal", "responsable_conformite", "clercs"])
async def test_ponderations_refusees_aux_non_admins(client, db, role):
    """SCO-02 : « Modifier les pondérations des axes » = O pour l'Admin, N pour les autres."""
    user = await utilisateur(db, role)
    reponse = await client.put(
        "/api/scoring/weights",
        json={"weights": {"montant": 2.0}},
        headers=auth_headers(user),
    )
    assert reponse.status_code == 403, (
        f"le rôle {role} ne doit pas pouvoir modifier la matrice de risque (SCO-02/ADM-03)"
    )


async def test_ponderations_modifiables_par_admin_et_prises_en_compte(
    client, db, config_scoring_restauree
):
    """SCO-02 : l'Admin ajuste les pondérations, et le calcul en tient compte.

    Une pondération que l'API accepte mais que le moteur ignore serait pire
    qu'une absence de fonctionnalité : le cabinet croirait avoir calibré sa
    matrice de risque.
    """
    admin = await utilisateur(db, "admin")
    user, dossier = await _dossier_pour(client, db)

    # Score de référence : seul l'axe « montant » est à 2 → 2/20, FAIBLE.
    axes = {**AXES_NULS, "montant": 2}
    reponse = await client.post(
        f"/api/dossiers/{dossier.id}/scoring/calculate",
        json={"axes": axes},
        headers=auth_headers(user),
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["total"] == 2

    # L'Admin quadruple la pondération de l'axe « montant ».
    maj = await client.put(
        "/api/scoring/weights",
        json={"weights": {"montant": 4.0}},
        headers=auth_headers(admin),
    )
    assert maj.status_code == 200, maj.text
    assert maj.json()["montant"] == 4.0

    reponse = await client.post(
        f"/api/dossiers/{dossier.id}/scoring/calculate",
        json={"axes": axes},
        headers=auth_headers(user),
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["total"] == 8, "la pondération Admin doit peser sur le score (SCO-02)"


async def test_ponderations_lisibles_par_tout_utilisateur_authentifie(client, db):
    """SCO-01 : le score et sa matrice sont consultables ; seule l'écriture est réservée."""
    user = await utilisateur(db, "responsable_conformite")
    reponse = await client.get("/api/scoring/weights", headers=auth_headers(user))
    assert reponse.status_code == 200, reponse.text
    config = reponse.json()
    for code in scoring_service.AXIS_CODES:
        assert code in config, f"pondération de l'axe « {code} » absente de la configuration"


async def test_les_dix_axes_du_cdc_sont_tous_presents():
    """CDC §2.4 : la matrice comporte exactement 10 axes, chacun noté 0, 1 ou 2."""
    assert len(scoring_service.AXIS_CODES) == 10
    assert len(set(scoring_service.AXIS_CODES)) == 10, "codes d'axes dupliqués"

    resultat = scoring_service.calculate({code: 2 for code in scoring_service.AXIS_CODES})
    assert resultat.score == 20, "10 axes × 2 points = 20, le maximum du CDC §2.1"

    # Une valeur hors barème est ramenée dans {0, 1, 2} plutôt que d'inflater le score.
    hors_bareme = scoring_service.calculate({**AXES_NULS, "montant": 99})
    assert hors_bareme.axes["montant"] == 2


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 2 — Triggers absolutoires T1 à T6 (CDC §2.3)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("code", "arguments"),
    [
        ("T1", {"est_ppe": True}),
        ("T2", {"mode_paiement": "especes", "montant_transaction": SEUIL_ESPECES_ART_72 + 1}),
        ("T3", {"sur_liste_sanctions": True}),
        ("T4", {"pays_liste_noire_gafi": True}),
        ("T5", {"refus_documents": True}),
        ("T6", {"be_non_identifiable": True}),
    ],
)
async def test_chaque_trigger_force_eleve_malgre_un_score_faible(tenant_a, code, arguments):
    """CDC §2.3 : chaque trigger force ÉLEVÉ « indépendamment du score de base ».

    Le score de base est volontairement fixé à 2/20 (FAIBLE) : si la
    classification restait FAIBLE, le dossier échapperait à la vigilance
    renforcée alors même qu'un critère absolutoire est avéré.

    Le calcul est placé dans le contexte d'un cabinet : le seuil espèces de T2
    est une configuration propre à chaque cabinet, et le moteur refuse — à
    raison — de scorer hors de tout cabinet.
    """
    with tenant_scope(tenant_a):
        resultat = scoring_service.calculate({**AXES_NULS, "montant": 2}, **arguments)
    assert resultat.score == 2, "le score de base doit rester inchangé — le trigger n'est pas un malus"
    assert resultat.classification == "ELEVE", f"{code} doit forcer ÉLEVÉ (CDC §2.3)"
    assert resultat.force_par_trigger is True
    assert code in resultat.triggers_actifs


async def test_trigger_t4_declenche_aussi_sur_la_liste_grise_gafi():
    """T4 : « pays classé liste noire OU liste grise GAFI » (CDC §2.3, Art. 30).

    Le CDC vise les deux listes ; ne retenir que la liste noire laisserait passer
    les juridictions sous surveillance renforcée du GAFI.
    """
    resultat = scoring_service.calculate(AXES_NULS, pays_liste_grise_gafi=True)
    assert resultat.classification == "ELEVE"
    assert "T4" in resultat.triggers_actifs


async def test_triggers_non_desactivables_par_les_axes():
    """CDC §2.3 : les triggers sont « verrouillés et non désactivables ».

    On met tous les axes à 0 — c'est-à-dire le dossier le plus anodin possible —
    et l'on vérifie qu'aucune saisie d'axe ne neutralise le trigger. En
    particulier l'axe 7 (PPE) mis à 0 ne doit pas annuler T1 : le statut PPE est
    dérivé de la fiche KYC, pas d'une case que l'agent contrôle.
    """
    resultat = scoring_service.calculate({**AXES_NULS, "ppe": 0}, est_ppe=True)
    assert resultat.score == 0
    assert resultat.classification == "ELEVE"
    assert "T1" in resultat.triggers_actifs


async def test_triggers_cumules_restent_tous_traces():
    """Plusieurs triggers simultanés doivent tous être conservés.

    Le registre des alertes (CDC §5.1) recense « les clients sur lesquels des
    triggers absolutoires ont été déclenchés » : n'en garder qu'un ferait
    disparaître des motifs de vigilance de la piste d'audit.
    """
    resultat = scoring_service.calculate(
        AXES_NULS, est_ppe=True, sur_liste_sanctions=True, be_non_identifiable=True
    )
    assert set(resultat.triggers_actifs) == {"T1", "T3", "T6"}
    assert resultat.trigger_principal == "T1", "le trigger principal suit l'ordre T1→T6 du CDC"


# ── T2 — seuil espèces Art. 72 ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("montant", "doit_declencher"),
    [
        (SEUIL_ESPECES_ART_72 - 1, False),
        (SEUIL_ESPECES_ART_72, False),      # « > 15M » : le seuil pile ne déclenche pas
        (SEUIL_ESPECES_ART_72 + 1, True),   # premier franc au-dessus : T2
    ],
)
async def test_t2_borne_exacte_du_seuil_especes(tenant_a, montant, doit_declencher):
    """T2 (Art. 72) : « Montant > 15 millions FCFA réglé en espèces ».

    L'inégalité est stricte : 15 000 000 FCFA exactement ne déclenche pas, mais
    15 000 001 FCFA oui. Une confusion `>=`/`>` produirait ici des déclarations
    CENTIF injustifiées, ou pire, une non-détection.
    """
    with tenant_scope(tenant_a):
        resultat = scoring_service.calculate(
            AXES_NULS, mode_paiement="especes", montant_transaction=montant
        )
    assert ("T2" in resultat.triggers_actifs) is doit_declencher
    assert (resultat.classification == "ELEVE") is doit_declencher


async def test_t2_ne_declenche_que_pour_un_reglement_en_especes(tenant_a):
    """T2 vise le règlement EN ESPÈCES (Art. 72) — un virement du même montant ne le déclenche pas.

    L'axe 4 « montant » reste à 2 dans les deux cas : le trigger n'est pas une
    fonction du seul montant, mais du couple montant × moyen de paiement.
    """
    with tenant_scope(tenant_a):
        virement = scoring_service.calculate(
            AXES_NULS, mode_paiement="virement", montant_transaction=SEUIL_ESPECES_ART_72 * 10
        )
        especes = scoring_service.calculate(
            AXES_NULS, mode_paiement="especes", montant_transaction=SEUIL_ESPECES_ART_72 * 10
        )
    assert "T2" not in virement.triggers_actifs
    assert "T2" in especes.triggers_actifs


async def test_t2_borne_exacte_via_api(client, db):
    """T2 de bout en bout : 15 000 000 FCFA en espèces ne bloque pas, 15 000 001 oui."""
    user, dossier = await _dossier_pour(client, db)

    au_seuil = await _calculer(
        client, user, dossier.id,
        montant_transaction=SEUIL_ESPECES_ART_72, mode_paiement="especes",
    )
    assert au_seuil.status_code == 200, au_seuil.text
    assert "T2" not in au_seuil.json()["triggers_actifs"]

    au_dessus = await _calculer(
        client, user, dossier.id,
        montant_transaction=SEUIL_ESPECES_ART_72 + 1, mode_paiement="especes",
    )
    assert au_dessus.status_code == 200, au_dessus.text
    corps = au_dessus.json()
    assert "T2" in corps["triggers_actifs"]
    assert corps["niveau"] == "ELEVE"


async def test_seuil_especes_ne_peut_pas_etre_releve_au_dessus_du_plafond_legal(
    client, db, config_scoring_restauree
):
    """Art. 72 + CDC §2.3 : les triggers absolutoires sont « non paramétrables ».

    Le paramétrage du seuil espèces (FR-26) est admis tant qu'il RENFORCE la
    vigilance — un cabinet peut décider de surveiller dès 5M FCFA. Le relever
    au-dessus de 15M reviendrait en revanche à désactiver T2 sur toute la plage
    légalement couverte, ce que ni l'Art. 72 ni le CDC n'autorisent, fût-ce à
    l'Administrateur.
    """
    admin = await utilisateur(db, "admin")

    # Durcissement autorisé : seuil abaissé.
    abaissement = await client.put(
        "/api/scoring/weights",
        json={"seuil_especes_t2_fcfa": 5_000_000},
        headers=auth_headers(admin),
    )
    assert abaissement.status_code == 200, abaissement.text
    assert abaissement.json()["seuil_especes_t2_fcfa"] == 5_000_000

    # Assouplissement interdit : seuil relevé au-delà du plafond de l'Art. 72.
    relevement = await client.put(
        "/api/scoring/weights",
        json={"seuil_especes_t2_fcfa": 100_000_000},
        headers=auth_headers(admin),
    )
    assert relevement.status_code == 422, (
        "relever le seuil espèces au-dessus de 15M FCFA désactiverait T2 (Art. 72)"
    )

    # Et le seuil en vigueur n'a pas bougé.
    lecture = await client.get("/api/scoring/weights", headers=auth_headers(admin))
    assert lecture.json()["seuil_especes_t2_fcfa"] == 5_000_000


# ── T3 — blocage immédiat (Art. 89) ───────────────────────────────────────────


async def test_t3_bloque_immediatement_le_dossier(client, db, tenant_a):
    """T3 (Art. 89) : « Classification forcée ÉLEVÉ — Blocage immédiat ».

    Le gel des avoirs prévu à l'Art. 89 n'a de sens que si l'opération est
    effectivement suspendue : classer ÉLEVÉ sans bloquer laisserait le cabinet
    instrumenter un acte au profit d'une personne sous sanctions.
    """
    user, dossier = await _dossier_pour(client, db)

    reponse = await _calculer(client, user, dossier.id, sur_liste_sanctions=True)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["niveau"] == "ELEVE"
    assert "T3" in corps["triggers_actifs"]

    relecture = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(user))
    assert relecture.status_code == 200, relecture.text
    assert relecture.json()["statut"] == "bloque", "T3 doit suspendre l'opération (Art. 89)"

    # Le drapeau `is_bloque` n'est pas exposé par `DossierOut` : on le contrôle en
    # base, car c'est lui qui matérialise la suspension pour les autres modules.
    with tenant_scope(tenant_a):
        bloque = (await db.execute(
            text(f'SELECT is_bloque FROM "{tenant_a.schema}".dossiers WHERE id = :did'),
            {"did": dossier.id},
        )).scalar_one()
    assert bloque is True, "le dossier doit porter le drapeau de blocage (Art. 89)"


async def test_les_autres_triggers_ne_bloquent_pas_le_dossier(client, db):
    """Seul T3 emporte blocage automatique (CDC §2.3).

    T1 (PPE) impose une vigilance renforcée, pas une suspension : bloquer tout
    dossier PPE paralyserait le cabinet et sortirait de ce que prévoit l'Art. 29.
    """
    user, dossier = await _dossier_pour(client, db)
    reponse = await _calculer(client, user, dossier.id, refus_documents=True)
    assert reponse.status_code == 200, reponse.text
    assert "T5" in reponse.json()["triggers_actifs"]

    relecture = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(user))
    assert relecture.json()["statut"] != "bloque"


# ── Persistance de l'évaluation ───────────────────────────────────────────────


async def test_evaluation_persistee_sur_le_dossier(client, db):
    """CDC §5.1 : le registre des dossiers à risque élevé s'appuie sur le score persisté.

    Un score correct mais non enregistré rendrait le registre faux et
    incommunicable à la CENTIF (Art. 103).
    """
    user, dossier = await _dossier_pour(client, db)
    reponse = await client.post(
        f"/api/dossiers/{dossier.id}/scoring/calculate",
        json={"axes": axes_totalisant(14)},
        headers=auth_headers(user),
    )
    assert reponse.status_code == 200, reponse.text

    relecture = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(user))
    corps = relecture.json()
    assert corps["score_base"] == 14
    assert corps["classification"] == "ELEVE"


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 3 — Alertes & vigilance
# ═════════════════════════════════════════════════════════════════════════════


async def _alertes_du_dossier(client, user, dossier_id: str) -> list[dict]:
    reponse = await client.get(
        "/api/alertes", params={"dossier_id": dossier_id}, headers=auth_headers(user)
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["items"]


@pytest.mark.parametrize(
    ("code", "payload"),
    [
        ("T2", {"montant_transaction": SEUIL_ESPECES_ART_72 + 1, "mode_paiement": "especes"}),
        ("T3", {"sur_liste_sanctions": True}),
        ("T4", {"pays_liste_noire_gafi": True}),
        ("T5", {"refus_documents": True}),
        ("T6", {"be_non_identifiable": True}),
    ],
)
async def test_alerte_creee_automatiquement_sur_trigger(client, db, code, payload):
    """CDC Module 3 « Détection automatique » : chaque trigger absolutoire génère une alerte.

    Le CDC énumère explicitement T1 à T6 parmi les détections automatiques. Sans
    alerte, le trigger n'apparaît ni dans le registre des alertes (CDC §5.1) ni
    dans la file de traitement du Responsable conformité : il est détecté mais
    personne n'en est informé.
    """
    user, dossier = await _dossier_pour(client, db)
    reponse = await _calculer(client, user, dossier.id, **payload)
    assert reponse.status_code == 200, reponse.text

    types = {a["type_alerte"] for a in await _alertes_du_dossier(client, user, dossier.id)}
    assert any(code in t for t in types), (
        f"aucune alerte générée pour le trigger {code} (CDC Module 3 — détection automatique) ; "
        f"types présents : {sorted(types)}"
    )


async def test_alerte_trigger_niveau_eleve(client, db):
    """CDC Module 3 : un trigger absolutoire classe ÉLEVÉ — l'alerte doit en hériter."""
    user, dossier = await _dossier_pour(client, db)
    await _calculer(client, user, dossier.id, be_non_identifiable=True)
    alertes = await _alertes_du_dossier(client, user, dossier.id)
    assert alertes, "aucune alerte générée pour T6"
    assert all(a["niveau"] == "ELEVE" for a in alertes)


async def test_pas_de_doublon_d_alerte_sur_recalcul(client, db):
    """Recalculer un score ne doit pas empiler des alertes identiques.

    Le scoring est rejoué à chaque enregistrement du KYC : sans garde-fou, le
    registre des alertes se remplit de doublons et devient inexploitable pour le
    Responsable conformité comme pour un contrôle CENTIF.
    """
    user, dossier = await _dossier_pour(client, db)
    for _ in range(3):
        reponse = await _calculer(client, user, dossier.id, refus_documents=True)
        assert reponse.status_code == 200, reponse.text

    alertes = await _alertes_du_dossier(client, user, dossier.id)
    t5 = [a for a in alertes if "T5" in a["type_alerte"]]
    assert len(t5) == 1, f"{len(t5)} alertes T5 pour un même dossier — doublons non consolidés"


async def test_aucune_alerte_pour_un_dossier_faible(client, db):
    """CDC Module 3 : niveau FAIBLE → « Validation simple — Aucune alerte générée ».

    Alerter sur un dossier faible noierait les alertes réellement significatives.
    """
    user, dossier = await _dossier_pour(client, db)
    reponse = await client.post(
        f"/api/dossiers/{dossier.id}/scoring/calculate",
        json={"axes": axes_totalisant(4)},
        headers=auth_headers(user),
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["niveau"] == "FAIBLE"
    assert await _alertes_du_dossier(client, user, dossier.id) == []


async def test_cycle_de_traitement_d_une_alerte(client, db):
    """ALE-01 / ALE-02 : consulter puis traiter une alerte, avec justification tracée."""
    user, dossier = await _dossier_pour(client, db)
    await _calculer(client, user, dossier.id, be_non_identifiable=True)
    alertes = await _alertes_du_dossier(client, user, dossier.id)
    assert alertes, "aucune alerte à traiter"
    alerte_id = alertes[0]["id"]

    # ALE-01 — consultation unitaire. L'API remonte le statut en MAJUSCULES
    # (contrat du frontend) alors que la base le stocke en minuscules : on
    # compare donc sans tenir compte de la casse.
    detail = await client.get(f"/api/alertes/{alerte_id}", headers=auth_headers(user))
    assert detail.status_code == 200, detail.text
    assert detail.json()["statut"].lower() == "ouverte"

    # Prise en charge puis traitement (ALE-02) — la justification est obligatoire.
    prise = await client.post(f"/api/alertes/{alerte_id}/prendre", headers=auth_headers(user))
    assert prise.status_code == 200, prise.text
    assert prise.json()["statut"].lower() == "en_cours"

    traitement = await client.post(
        f"/api/alertes/{alerte_id}/traiter",
        json={"justification": "Bénéficiaire effectif identifié après diligences complémentaires."},
        headers=auth_headers(user),
    )
    assert traitement.status_code == 200, traitement.text
    assert traitement.json()["statut"].lower() == "traitee"


async def test_blocage_manuel_du_dossier_depuis_une_alerte(client, db):
    """ALE-03 : « Bloquer un dossier manuellement » — O pour Admin, Notaire et RC."""
    user, dossier = await _dossier_pour(client, db)
    await _calculer(client, user, dossier.id, refus_documents=True)
    alertes = await _alertes_du_dossier(client, user, dossier.id)
    assert alertes, "aucune alerte disponible pour le blocage manuel"
    alerte_id = alertes[0]["id"]

    blocage = await client.post(
        f"/api/alertes/{alerte_id}/bloquer-dossier", headers=auth_headers(user)
    )
    assert blocage.status_code == 200, blocage.text
    assert blocage.json()["status"] == "bloque"

    relecture = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(user))
    assert relecture.json()["statut"] == "bloque"

    deblocage = await client.post(
        f"/api/alertes/{alerte_id}/debloquer-dossier", headers=auth_headers(user)
    )
    assert deblocage.status_code == 200, deblocage.text


async def test_clerc_ne_peut_ni_traiter_ni_bloquer(client, db):
    """ALE-02 / ALE-03 = N pour les Clercs (CDC §7.3, séparation des fonctions Art. 12)."""
    rc, dossier = await _dossier_pour(client, db)
    await _calculer(client, rc, dossier.id, refus_documents=True)
    alertes = await _alertes_du_dossier(client, rc, dossier.id)
    alerte_id = alertes[0]["id"]

    clerc = await utilisateur(db, "clercs")

    traitement = await client.post(
        f"/api/alertes/{alerte_id}/traiter",
        json={"justification": "tentative"},
        headers=auth_headers(clerc),
    )
    assert traitement.status_code == 403, "un clerc ne traite pas une alerte (ALE-02)"

    blocage = await client.post(
        f"/api/alertes/{alerte_id}/bloquer-dossier", headers=auth_headers(clerc)
    )
    assert blocage.status_code == 403, "un clerc ne bloque pas un dossier (ALE-03)"


async def test_clerc_peut_signaler_une_suspicion(client, db):
    """DOS-01 : « Signaler une suspicion (flag interne) » = O pour les Clercs (Art. 60).

    L'obligation générale de vigilance de l'Art. 60 pèse sur tout collaborateur :
    le clerc doit pouvoir remonter un doute sans avoir le droit de le traiter.
    """
    clerc = await utilisateur(db, "clercs")
    reponse = await client.post(
        "/api/alertes/signaler",
        json={"description": "Le client refuse d'expliquer l'origine des fonds."},
        headers=auth_headers(clerc),
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["type_alerte"] == "SIGNALEMENT_INTERNE"


# ═════════════════════════════════════════════════════════════════════════════
# MODULE 1 — Gestion des clients (KYC)
# ═════════════════════════════════════════════════════════════════════════════


def _payload_kyc_pp(**extra) -> dict:
    """Fiche PP minimale couvrant les sections du CDC §1.1."""
    return {
        "nom": "KOUASSI",
        "prenoms": "Ama Grace",
        "sexe": "F",
        "date_naissance": "1985-04-12",
        "lieu_naissance": "Abidjan",
        "nationalite": "Ivoirienne",
        "statut_matrimonial": "Mariée",
        "type_piece": "CNI",
        "numero_piece": f"CI-{uuid.uuid4().hex[:10].upper()}",
        "pays_emetteur_piece": "CI",
        "mode_verification_piece": "original_vu",
        "adresse_geo": "Cocody, Riviera 3",
        "telephone": "+225 07 00 00 00 01",
        "whatsapp": "+225 07 00 00 00 02",
        "email": "ama.kouassi@example.ci",
        "pays_residence": "CI",
        "ville_residence": "Abidjan",
        "profession": "Ingénieure",
        "employeur": "SODECI",
        "tranche_revenus": "2m_10m",
        "numero_contribuable": "CC-9988776655",
        **extra,
    }


async def test_cycle_complet_fiche_kyc_pp(client, db):
    """KYC-01/02/05 : créer, relire puis modifier une fiche personne physique (Art. 16-17)."""
    user, dossier = await _dossier_pour(client, db, type_client="PP")

    creation = await client.put(
        f"/api/dossiers/{dossier.id}/kyc/pp",
        json=_payload_kyc_pp(),
        headers=auth_headers(user),
    )
    assert creation.status_code == 200, creation.text
    assert creation.json()["nom"] == "KOUASSI"

    lecture = await client.get(f"/api/dossiers/{dossier.id}/kyc/pp", headers=auth_headers(user))
    assert lecture.status_code == 200, lecture.text
    fiche = lecture.json()
    assert fiche["prenoms"] == "Ama Grace"
    # Les champs sensibles sont bien restitués en clair à l'utilisateur habilité :
    # le chiffrement au repos (CDC §5.2) doit rester transparent à l'usage.
    assert fiche["telephone"] == "+225 07 00 00 00 01"
    assert fiche["email"] == "ama.kouassi@example.ci"

    modification = await client.put(
        f"/api/dossiers/{dossier.id}/kyc/pp",
        json=_payload_kyc_pp(profession="Directrice financière"),
        headers=auth_headers(user),
    )
    assert modification.status_code == 200, modification.text
    assert modification.json()["profession"] == "Directrice financière"


async def test_kyc_pp_refuse_une_identite_incomplete(client, db):
    """Art. 16-17 : l'identification est un préalable — nom et prénoms sont obligatoires."""
    user, dossier = await _dossier_pour(client, db, type_client="PP")
    incomplet = _payload_kyc_pp()
    del incomplet["nom"]

    reponse = await client.put(
        f"/api/dossiers/{dossier.id}/kyc/pp", json=incomplet, headers=auth_headers(user)
    )
    assert reponse.status_code == 422, "une fiche sans nom ne doit pas être enregistrable"


async def test_kyc_pp_declaration_ppe_declenche_t1(client, db):
    """CDC §1.1 + T1 : déclarer un statut PPE reclasse la fiche en ÉLEVÉ (Art. 29).

    Le trigger doit naître de la donnée KYC elle-même, sans que l'agent ait à
    cocher quoi que ce soit dans l'écran de scoring : c'est ce qui rend T1
    non contournable.
    """
    user, dossier = await _dossier_pour(client, db, type_client="PP")
    reponse = await client.put(
        f"/api/dossiers/{dossier.id}/kyc/pp",
        json=_payload_kyc_pp(est_ppe=True, ppe_categorie="national"),
        headers=auth_headers(user),
    )
    assert reponse.status_code == 200, reponse.text

    relecture = await client.get(f"/api/dossiers/{dossier.id}", headers=auth_headers(user))
    corps = relecture.json()
    assert corps["classification"] == "ELEVE", "un client PPE doit être classé ÉLEVÉ (T1, Art. 29)"
    assert corps["trigger_actif"] == "T1"


async def test_cycle_complet_fiche_kyc_pm_avec_be_et_actionnaires(client, db):
    """CDC §1.2 : fiche PM, structure du capital et bénéficiaires effectifs ≥ 25% (Art. 12b)."""
    user, dossier = await _dossier_pour(client, db, type_client="PM")

    creation = await client.put(
        f"/api/dossiers/{dossier.id}/kyc/pm",
        json={
            "denomination_sociale": "SCI Les Palmiers",
            "forme_juridique": "SARL",
            "numero_rccm": f"CI-ABJ-{uuid.uuid4().hex[:8].upper()}",
            "pays_constitution": "CI",
            "adresse": "Plateau, Rue du Commerce",
            "telephone": "+225 27 20 00 00 00",
            "email": "contact@palmiers.ci",
            "nom_representant_legal": "TRAORE Ibrahim",
        },
        headers=auth_headers(user),
    )
    assert creation.status_code == 200, creation.text
    assert creation.json()["denomination_sociale"] == "SCI Les Palmiers"

    # Bénéficiaire effectif détenant plus de 25% — seuil de l'Art. 12b.
    be = await client.post(
        f"/api/dossiers/{dossier.id}/kyc/pm/be",
        json={
            "raison_sociale_nom": "TRAORE Ibrahim",
            "pourcentage": 60.0,
            "pays_residence": "CI",
            "nationalite": "Ivoirienne",
        },
        headers=auth_headers(user),
    )
    assert be.status_code == 201, be.text
    assert be.json()["pourcentage"] == 60.0

    actionnaire = await client.post(
        f"/api/dossiers/{dossier.id}/kyc/pm/actionnaires",
        json={
            "raison_sociale_nom": "TRAORE Ibrahim",
            "type_personne": "PP",
            "pourcentage": 60.0,
            "ordre": 1,
        },
        headers=auth_headers(user),
    )
    assert actionnaire.status_code == 201, actionnaire.text

    lecture = await client.get(f"/api/dossiers/{dossier.id}/kyc/pm", headers=auth_headers(user))
    assert lecture.status_code == 200, lecture.text
    fiche = lecture.json()
    assert len(fiche["beneficiaires_effectifs"]) == 1
    assert len(fiche["actionnaires"]) == 1


async def test_documents_rattaches_a_la_fiche_client(client, db):
    """CDC §1.3 + KYC-03 : les pièces justificatives sont rattachées à la fiche et restituées.

    Le stockage passe exclusivement par l'API (CDC §5.2 : « accès via API
    uniquement, jamais par URL directe ») — la restitution est donc testée par
    le téléchargement authentifié, pas par une URL de stockage.
    """
    user, dossier = await _dossier_pour(client, db, type_client="PP")
    contenu = b"%PDF-1.4\n% piece d'identite de test\n"

    upload = await client.post(
        f"/api/dossiers/{dossier.id}/documents",
        files={"file": ("cni.pdf", contenu, "application/pdf")},
        data={"type_document": "piece_identite"},
        headers=auth_headers(user),
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["dossier_id"] == dossier.id
    assert document["type_document"] == "piece_identite"

    liste = await client.get(
        f"/api/dossiers/{dossier.id}/documents", headers=auth_headers(user)
    )
    assert liste.status_code == 200, liste.text
    assert document["id"] in {d["id"] for d in liste.json()}

    telechargement = await client.get(
        f"/api/documents/{document['id']}/download", headers=auth_headers(user)
    )
    assert telechargement.status_code == 200, telechargement.text
    assert telechargement.content == contenu


async def test_document_refuse_sans_authentification(client, db):
    """CDC §5.2 : aucun accès aux pièces hors API authentifiée."""
    user, dossier = await _dossier_pour(client, db, type_client="PP")
    upload = await client.post(
        f"/api/dossiers/{dossier.id}/documents",
        files={"file": ("cni.pdf", b"%PDF-1.4\ntest\n", "application/pdf")},
        data={"type_document": "piece_identite"},
        headers=auth_headers(user),
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["id"]

    anonyme = await client.get(f"/api/documents/{doc_id}/download")
    assert anonyme.status_code == 401


# ── Chiffrement au repos (CDC §5.2) ──────────────────────────────────────────


async def test_donnees_pii_chiffrees_en_base(client, db, tenant_a):
    """CDC §5.2 : « chiffrement AES-256 au niveau base de données pour les champs sensibles ».

    La vérification se fait en lecture BRUTE sur le schéma du cabinet, hors ORM :
    passer par le modèle déchiffrerait à la volée et le test validerait un
    chiffrement inexistant. Ce qui est éprouvé ici, c'est ce qu'un porteur d'une
    copie de la base verrait réellement.
    """
    user, dossier = await _dossier_pour(client, db, type_client="PP")
    telephone = "+225 05 55 44 33 22"
    piece = f"CI-{uuid.uuid4().hex[:10].upper()}"

    reponse = await client.put(
        f"/api/dossiers/{dossier.id}/kyc/pp",
        json=_payload_kyc_pp(telephone=telephone, numero_piece=piece),
        headers=auth_headers(user),
    )
    assert reponse.status_code == 200, reponse.text

    with tenant_scope(tenant_a):
        brut = (await db.execute(
            text(
                f'SELECT telephone, numero_piece, email, adresse_geo '
                f'FROM "{tenant_a.schema}".kyc_pp WHERE dossier_id = :did'
            ),
            {"did": dossier.id},
        )).mappings().one()

    for colonne, valeur_en_clair in (
        ("telephone", telephone),
        ("numero_piece", piece),
        ("email", "ama.kouassi@example.ci"),
        ("adresse_geo", "Cocody, Riviera 3"),
    ):
        stocke = brut[colonne]
        assert stocke, f"colonne {colonne} vide — le test ne prouve rien"
        assert valeur_en_clair not in stocke, (
            f"la colonne {colonne} contient la valeur en clair — CDC §5.2 non respecté"
        )
        assert stocke.startswith("enc::"), (
            f"la colonne {colonne} n'est pas chiffrée au repos (préfixe « enc:: » attendu)"
        )
