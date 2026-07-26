"""Cumul de rôles — une même personne (un seul email) porte plusieurs casquettes.

Cas courant en petite étude : le notaire principal tient aussi la conformité. On
ne duplique pas le compte (l'email reste la clé de connexion) : c'est
l'utilisateur qui porte plusieurs rôles.

Tests purement unitaires — `a_role()` est le point de passage de TOUTES les
autorisations, sa sémantique mérite d'être verrouillée sans dépendre d'une base.
"""
from app.models.user import ROLES_SUPERVISEURS, User


def _u(role: str, extra=None) -> User:
    return User(
        id="u1", email="x@etude.ci", hashed_password="x",
        first_name="A", last_name="B", role=role, roles_extra=extra,
    )


def test_roles_expose_le_principal_puis_les_cumules():
    u = _u("clercs", ["responsable_conformite"])
    # Le principal reste en tête : l'affichage et l'audit ne changent pas de sens.
    assert u.roles == ("clercs", "responsable_conformite")
    assert u.role == "clercs"


def test_a_role_reconnait_principal_et_cumul():
    u = _u("clercs", ["declarant_centif"])
    assert u.a_role("clercs")
    assert u.a_role("declarant_centif")
    assert u.a_role("admin", "declarant_centif")  # au moins un suffit
    assert not u.a_role("admin")


def test_sans_cumul_comportement_inchange():
    """Non-régression : un compte sans cumul se comporte exactement comme avant."""
    u = _u("clercs")
    assert u.roles == ("clercs",)
    assert not u.a_role("responsable_conformite")
    assert not u.is_supervisor


def test_un_role_cumule_confere_la_supervision():
    """Le point central : un clerc cumulant RC obtient la vue de supervision."""
    assert not _u("clercs").is_supervisor
    assert _u("clercs", ["responsable_conformite"]).is_supervisor


def test_role_inconnu_dans_le_cumul_est_ignore():
    """Une valeur héritée ou altérée ne doit conférer aucun droit."""
    u = _u("clercs", ["root", "notaire_principal"])
    assert u.roles == ("clercs", "notaire_principal")
    assert not u.a_role("root")


def test_a_role_accepte_un_ensemble():
    """Les contrôles passent souvent une constante (set/tuple) : `a_role(*ENSEMBLE)`."""
    u = _u("clercs", ["notaire_principal"])
    assert u.a_role(*ROLES_SUPERVISEURS)
    assert not _u("clercs").a_role(*ROLES_SUPERVISEURS)


def test_le_principal_n_est_jamais_duplique():
    u = _u("clercs", ["clercs", "declarant_centif"])
    assert u.roles == ("clercs", "declarant_centif")
