"""Verrou d'archivage réglementaire — Art. 23 et Art. 197, Ordonnance N°2023-875.

Le CDC §5.2 « Archivage — Règles de Conservation » fixe quatre règles que ce
module porte pour l'ensemble de l'applicatif :

* Déclencheur    — le passage en état « Clôturé » déclenche automatiquement
                   l'archivage (pas d'action manuelle, pas d'oubli possible) ;
* Durée          — 10 ans à compter de la date de clôture (Art. 23) ;
* Droits         — état « Archivé » = lecture seule, « aucune modification
                   possible par aucun rôle » ;
* Suppression    — impossible avant 10 ans, bloquée au niveau base de données
                   (trigger `prevent_archive_delete`), car sa destruction est
                   une infraction pénale (Art. 197 — 6 mois à 2 ans + amende).

Le garde-fou applicatif ci-dessous ne remplace pas le trigger PostgreSQL : il le
complète. Le trigger interdit l'effacement, ce module interdit l'altération —
deux atteintes distinctes à l'intégrité de la piste d'archivage.
"""
from datetime import date

from fastapi import HTTPException, status

# Art. 23 — conservation des pièces pendant 10 ans à compter de la clôture
# de la relation d'affaires. Constante et non paramétrable : aucun rôle, pas
# même l'Administrateur, ne peut raccourcir la durée légale de conservation.
DUREE_CONSERVATION_ANNEES = 10

_DETAIL_LECTURE_SEULE = (
    "Dossier archivé — lecture seule. Conservation légale de 10 ans (Art. 23, "
    "Ordonnance N°2023-875) : aucune modification n'est possible, quel que soit le rôle."
)


def date_expiration_conservation(date_cloture: date) -> date:
    """Échéance des 10 ans de conservation à compter de la clôture (Art. 23).

    Le 29 février est ramené au 28 : ajouter 10 ans à un 29/02 donnerait une
    date inexistante et lèverait une `ValueError` au moment précis de la clôture
    d'un dossier — soit un échec de l'archivage, c'est-à-dire l'inverse de ce que
    l'article impose.
    """
    try:
        return date_cloture.replace(year=date_cloture.year + DUREE_CONSERVATION_ANNEES)
    except ValueError:
        return date_cloture.replace(year=date_cloture.year + DUREE_CONSERVATION_ANNEES, day=28)


def declencher_archivage(dossier, aujourdhui: date | None = None) -> None:
    """Pose la date d'archivage et son échéance sur un dossier qui vient d'être clôturé.

    CDC §5.2 : « Le passage en état Clôturé déclenche automatiquement l'archivage ».
    Idempotent — une clôture rejouée ne repousse pas l'échéance des 10 ans, ce qui
    reviendrait à prolonger arbitrairement la conservation d'un dossier.
    """
    if dossier.archivage_date is not None:
        return
    jour = aujourdhui or date.today()
    dossier.archivage_date = jour
    dossier.archivage_expiration = date_expiration_conservation(jour)


def est_archive(dossier) -> bool:
    return getattr(dossier, "statut", None) == "archive"


def assert_dossier_modifiable(dossier) -> None:
    """Refuse toute écriture sur un dossier archivé (CDC §5.2 — lecture seule).

    Levée en 403 et non en 422 : il ne s'agit pas d'une donnée mal formée mais
    d'un droit qui n'existe pour personne — l'interdiction est absolue et ne
    dépend ni du rôle de l'appelant ni du contenu de la requête.
    """
    if est_archive(dossier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_DETAIL_LECTURE_SEULE,
        )
