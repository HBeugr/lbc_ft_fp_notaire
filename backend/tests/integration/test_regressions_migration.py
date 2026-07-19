"""Non-régressions de la migration MySQL → PostgreSQL SaaS.

Chaque test de ce module verrouille un défaut **réellement rencontré** pendant
la migration. Ils n'ont pas d'intérêt fonctionnel propre : leur rôle est
d'empêcher le retour d'erreurs qui, pour la plupart, ne se manifestaient qu'à
l'exécution — pas au typecheck, pas à la compilation, et pas sous MySQL.
"""
import logging

import pytest

# Les cabinets de test sont provisionnés une seule fois : les tests asynchrones
# doivent partager la boucle d'événements de session. Le marqueur est posé test
# par test — appliqué au module, il alerterait sur les tests synchrones.
_boucle_session = pytest.mark.asyncio(loop_scope="session")

from app.core import dos_privileges
from app.core.config import settings
from tests.conftest import auth_headers, create_dossier, create_user


# ── 1. Tableau de bord : valeur absente de l'ENUM PostgreSQL ─────────────────

@_boucle_session
async def test_dashboard_stats_repond_pour_tous_les_roles(client, db, tenant_a):
    """Le tableau de bord filtrait sur un statut `resilie` inexistant.

    MySQL acceptait la comparaison d'une colonne ENUM à une valeur hors
    énumération et ne renvoyait simplement aucune ligne ; PostgreSQL la rejette
    (`invalid input value for enum`), ce qui mettait toute la page d'accueil en
    erreur 500 — pour tous les rôles, dès la première connexion.
    """
    for role in ("notaire_principal", "responsable_conformite", "clercs", "admin"):
        utilisateur = await create_user(db, role=role)
        reponse = await client.get("/api/dashboard/stats", headers=auth_headers(utilisateur, tenant_a))
        assert reponse.status_code == 200, f"rôle {role} : {reponse.text}"


@_boucle_session
async def test_dashboard_stats_avec_dossiers_de_tous_statuts(client, db, tenant_a):
    """Chaque statut valide doit traverser l'agrégation sans erreur."""
    utilisateur = await create_user(db, role="notaire_principal")
    for statut in ("brouillon", "en_analyse", "vigilance_renforcee", "valide",
                   "bloque", "traite", "cloture", "archive"):
        await create_dossier(db, created_by=utilisateur.id, statut=statut)

    reponse = await client.get("/api/dashboard/stats", headers=auth_headers(utilisateur, tenant_a))
    assert reponse.status_code == 200, reponse.text


# ── 2. Séparation de privilèges du rôle DOS ─────────────────────────────────

@_boucle_session
async def test_role_dos_refuse_si_identique_au_role_applicatif(monkeypatch):
    """`DOS_DB_USER == DB_USER` doit être refusé, pas « fait au mieux ».

    Deux conséquences si on laissait passer : la séparation de privilèges de
    l'Art. 63 disparaît (le rôle « restreint » est le superutilisateur, donc
    DELETE sur les DOS redevient possible), et l'`ALTER ROLE` de démarrage
    réinitialise le mot de passe du compte applicatif — l'application se
    verrouille hors de sa propre base au redémarrage suivant.
    """
    monkeypatch.setattr(settings, "DOS_DB_USER", settings.DB_USER)

    class _SessionSentinelle:
        """Échoue si le code tente malgré tout d'exécuter du DDL."""

        async def execute(self, *_args, **_kwargs):  # pragma: no cover
            raise AssertionError("aucun DDL ne doit être émis dans ce cas")

    assert await dos_privileges.ensure_role(_SessionSentinelle()) is False


@_boucle_session
async def test_role_dos_refuse_un_identifiant_invalide(monkeypatch):
    """Le nom de rôle est interpolé dans du DDL : il doit être validé."""
    monkeypatch.setattr(settings, "DOS_DB_USER", 'dos"; DROP SCHEMA shared CASCADE; --')

    class _SessionSentinelle:
        async def execute(self, *_args, **_kwargs):  # pragma: no cover
            raise AssertionError("aucun DDL ne doit être émis pour un identifiant invalide")

    assert await dos_privileges.ensure_role(_SessionSentinelle()) is False


# ── 3. Aucun secret dans les journaux ───────────────────────────────────────

def test_echo_sql_neutralise_puis_restaure():
    """Le DDL de rôle porte un mot de passe en clair (PostgreSQL n'admet pas de
    paramètre lié en DDL) : l'écho SQL doit être éteint le temps de l'exécuter,
    puis rétabli — sans quoi les journaux perdent toute valeur de diagnostic.
    """
    from app.core.database import _get_engine

    moteur = _get_engine()
    echo_initial = moteur.echo
    moteur.echo = True
    try:
        with dos_privileges._muted_sql_echo():
            assert moteur.echo is False, "l'écho doit être coupé pendant le DDL sensible"
            for nom in dos_privileges._SQL_ECHO_LOGGERS:
                assert logging.getLogger(nom).level >= logging.WARNING
        assert moteur.echo is True, "l'écho doit être rétabli après le DDL"
    finally:
        moteur.echo = echo_initial


def test_quote_literal_neutralise_les_apostrophes():
    """Échappement du mot de passe interpolé dans le DDL."""
    assert dos_privileges._quote_literal("a'b") == "'a''b'"
    assert dos_privileges._quote_literal("simple") == "'simple'"


# ── 4. Provisioning indépendant du PATH ─────────────────────────────────────

def test_provisioning_invoque_alembic_par_l_interpreteur_courant():
    """`alembic` était appelé en tant que binaire, donc dépendant du PATH.

    Selon la façon dont l'application est lancée (superviseur, cron, tests avec
    un environnement vierge), le binaire peut être absent alors que le module
    est parfaitement installé. On passe par `sys.executable -m alembic`, ce qui
    garantit en prime le même environnement virtuel que l'application.
    """
    import inspect

    from app.services import tenant_provisioning

    source = inspect.getsource(tenant_provisioning._run_alembic)
    assert "sys.executable" in source
    assert '"-m", "alembic"' in source
    # Le répertoire de travail est explicite : `alembic.ini` doit être résolu
    # quel que soit le répertoire courant du processus.
    assert "cwd=_BACKEND_ROOT" in source


# ── 5. Invariants de configuration (infrastructure) ─────────────────────────
#
# Ces défauts-là ne vivent pas dans le code Python mais dans les fichiers de
# déploiement. Ils sont vérifiés ici parce qu'ils ont exactement les mêmes
# conséquences qu'un bug applicatif — exposition de données ou indisponibilité —
# et qu'aucun autre garde-fou ne les attraperait.

from pathlib import Path

_RACINE = Path(__file__).resolve().parents[3]

# Ces contrôles portent sur des fichiers du dépôt, absents de l'image Docker
# (seul `backend/` y est copié). Les ignorer proprement dans ce cas évite quatre
# faux échecs quand la suite est lancée depuis le conteneur.
_hors_depot = pytest.mark.skipif(
    not (_RACINE / "docker-compose.yml").exists(),
    reason="fichiers de déploiement absents (suite exécutée hors du dépôt)",
)


def _lire(nom: str) -> str:
    return (_RACINE / nom).read_text()


def _valeurs_env(nom: str) -> dict[str, str]:
    valeurs = {}
    for ligne in _lire(nom).splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.strip()
    return valeurs


@_hors_depot
def test_minio_non_publie_en_production():
    """Le stockage documentaire ne doit pas être joignable depuis l'hôte.

    Il n'est consommé que par l'API, sur le réseau interne. Le publier exposerait
    actes et pièces d'identité derrière une simple clé S3, sans aucun besoin.
    """
    compose = _lire("docker-compose.yml")
    assert "9010:9000" not in compose
    assert "9011:9001" not in compose


@_hors_depot
def test_app_env_production_dans_les_fichiers_denvironnement():
    """`APP_ENV=development` sur la pile déployée active l'écho SQL — requêtes
    ET paramètres recopiés dans les journaux, données clients comprises — et
    expose `/api/docs`. Le développement local passe par docker-compose.dev.yml,
    qui force `development` sur le service `api`.
    """
    for fichier in (".env", ".env.example"):
        assert _valeurs_env(fichier).get("APP_ENV") == "production", fichier


@_hors_depot
def test_role_dos_distinct_du_role_applicatif_dans_lenvironnement():
    """Séparation de privilèges DOS (ADR-003, Art. 63) — voir le garde-fou
    applicatif plus haut, dont ceci est le pendant côté configuration."""
    for fichier in (".env", ".env.example"):
        valeurs = _valeurs_env(fichier)
        assert valeurs.get("DOS_DB_USER") != valeurs.get("DB_USER"), fichier


@_hors_depot
def test_ports_de_developpement_sans_conflit_avec_les_autres_verticaux():
    """Les trois verticaux LBC/FT cohabitent sur le même poste et le même VPS.

    Le vertical assujetti occupe 5433 (PostgreSQL), 6380 (Redis) et 9010/9011
    (MinIO). Réutiliser ces ports empêche purement et simplement de démarrer les
    deux piles en parallèle.
    """
    dev = _lire("docker-compose.dev.yml")
    for port_occupe in ("5433:5432", "6380:6379", "9010:9000", "9011:9001"):
        assert f'"{port_occupe}"' not in dev, f"port {port_occupe} déjà pris par le vertical assujetti"
