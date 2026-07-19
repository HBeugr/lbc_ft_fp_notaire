"""Criblage des listes de sanctions — entrées portant un alias en ligne.

Défaut réel constaté sur les données de production : la liste nationale 1373
consigne les pseudonymes DANS le champ nom, sous la forme
« SIDAT MOUCTARR FAAL ALIAS « DADDYFALL » ». Comparé à la chaîne entière, le
vrai nom obtenait un score de 66 pour un seuil de 85 : **la personne, pourtant
listée, n'était pas détectée** si l'on saisissait son nom réel — ce que fait
naturellement un notaire.

12 des 76 entrées de cette liste étaient concernées, soit 16 %. C'est un défaut
de détection du trigger T3 (Art. 89), pas une question de confort de recherche.
"""
import pytest

from app.services import sanctions_service


class _Entree:
    def __init__(self, nom, date_naissance=None, lieu_naissance=None, nationalite=None):
        self.nom = nom
        self.date_naissance = date_naissance
        self.lieu_naissance = lieu_naissance
        self.nationalite = nationalite


class _Liste:
    def __init__(self, nom, entrees, type_liste="AUTRE"):
        self.nom = nom
        self.type_liste = type_liste
        self.entrees = entrees


_ENTREE_1373 = "SIDAT MOUCTARR FAAL ALIAS « DADDYFALL »"


def test_variantes_extrait_nom_et_alias():
    variantes = sanctions_service.variantes_nom(_ENTREE_1373)
    assert "SIDAT MOUCTARR FAAL" in variantes, "le nom réel doit être comparable seul"
    assert "DADDYFALL" in variantes, "l'alias doit être comparable seul"
    assert _ENTREE_1373 in variantes, "la chaîne complète reste comparable"


@pytest.mark.parametrize("recherche", [
    "SIDAT MOUCTARR FAAL",   # le nom réel — cas qui échouait
    "DADDYFALL",             # l'alias seul
    "SIDAT MOUCTARR FAAL ALIAS DADDYFALL",
])
def test_entree_avec_alias_detectee(recherche):
    """Chacune des trois façons de désigner la personne doit la retrouver."""
    listes = [_Liste("Liste nationale 1373", [_Entree(_ENTREE_1373)])]
    resultat = sanctions_service.pre_check(nom=recherche, listes=listes)
    assert resultat["level"] in ("blocked", "warning"), (
        f"« {recherche} » doit être détecté — niveau obtenu : {resultat['level']}"
    )
    assert resultat["liste"] == "Liste nationale 1373"


def test_les_deux_listes_sont_criblees():
    """Aucun filtre par type de liste : nationale ET internationale sont interrogées."""
    listes = [
        _Liste("Liste nationale 1373", [_Entree("KOFFI YAO BERNARD")], type_liste="AUTRE"),
        _Liste("Liste ONU", [_Entree("SADRUDDIN")], type_liste="UE_CSDNU"),
    ]
    for recherche, attendue in [("KOFFI YAO BERNARD", "Liste nationale 1373"),
                                ("SADRUDDIN", "Liste ONU")]:
        resultat = sanctions_service.pre_check(nom=recherche, listes=listes)
        assert resultat["level"] in ("blocked", "warning")
        assert resultat["liste"] == attendue


def test_pas_de_faux_positif():
    """Le découpage des alias ne doit pas rendre le criblage laxiste."""
    listes = [_Liste("Liste nationale 1373", [_Entree(_ENTREE_1373)])]
    resultat = sanctions_service.pre_check(nom="DUPONT JEAN MICHEL", listes=listes)
    assert resultat["level"] == "clear", "un nom sans rapport ne doit pas ressortir"


def test_screen_applique_les_memes_variantes():
    """`screen()` (criblage formel, audité) et `pre_check()` (écran de saisie)
    doivent voir la même chose — sinon l'interface et le registre divergent."""
    listes = [_Liste("Liste nationale 1373", [_Entree(_ENTREE_1373)])]
    resultats = sanctions_service.screen(
        nom="SIDAT MOUCTARR FAAL", date_naissance=None, lieu_naissance=None,
        seuil=85, listes=listes,
    )
    assert resultats and resultats[0]["niveau"] != "no_match"
