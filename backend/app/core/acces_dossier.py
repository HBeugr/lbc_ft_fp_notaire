"""Droits d'accès à un dossier — la lecture et l'écriture, en un seul endroit.

Deux droits DISTINCTS, et leur confusion est la cause de l'incident remonté par
le cabinet (« Accès refusé » à l'enregistrement d'une fiche KYC) :

- **Lecture** : superviseur, assigné courant, ou **auteur du dossier**.
- **Écriture** : superviseur ou assigné courant. Un dossier routé vers un
  collègue passe donc en lecture seule pour son auteur — il le suit, il ne le
  modifie plus.

Le vertical immobilier applique exactement ce partage (`_assert_access` /
`_assert_can_modify`, avec une visibilité « assignés ou créés par eux »). Le
portage notarial n'avait retenu qu'une garde unique, servant à la fois la
lecture et l'écriture et ne connaissant que l'assignation : l'utilisateur qui
routait son propre dossier en perdait aussitôt jusqu'à la consultation, et le
dossier disparaissait de sa liste. Les quatre routeurs (kyc, scoring, documents,
dossiers) dupliquaient cette même garde, chacun avec sa variante — d'où ce
module unique.

Écart au CDC notarial, assumé et tracé : §7.3 note sous KYC-05 « P¹ = Clercs :
consultation limitée aux dossiers qui leur sont assignés uniquement ». La règle
vise la vue transversale, réservée aux superviseurs ; elle n'a pas pour objet de
retirer à un collaborateur la fiche qu'il a lui-même constituée. On y ajoute
donc l'auteur, comme le fait l'immobilier, sans jamais élargir l'écriture.
"""
from fastapi import HTTPException, status

ACCES_REFUSE = "Accès refusé."
LECTURE_SEULE = "Ce dossier est assigné à un autre utilisateur : vous y avez accès en lecture seule."


def peut_lire(user, dossier) -> bool:
    return (
        user.is_supervisor
        or dossier.assigned_to == user.id
        or dossier.created_by == user.id
    )


def peut_ecrire(user, dossier) -> bool:
    return user.is_supervisor or dossier.assigned_to == user.id


def assert_lecture(user, dossier) -> None:
    if not peut_lire(user, dossier):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCES_REFUSE)


def assert_ecriture(user, dossier) -> None:
    """Lecture d'abord — un tiers sans aucun droit ne doit pas apprendre, par la
    différence de message, qu'un dossier existe et à qui il est assigné."""
    assert_lecture(user, dossier)
    if not peut_ecrire(user, dossier):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=LECTURE_SEULE)
