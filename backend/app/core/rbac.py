"""
RBAC pour le projet notaire — mono-cabinet.

Deux types de filtres :
  - Superviseurs (admin, notaire_principal, responsable_conformite) : accès global
  - Clercs : uniquement les dossiers qui leur sont assignés (assigned_to = user.id)
"""

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User


class AssignedFilter:
    """Contrainte d'accès pour les clercs — dossiers assignés uniquement."""

    def __init__(self, user_id: str | None):
        self.user_id = user_id  # None = pas de filtre (superviseur)

    @property
    def is_global(self) -> bool:
        return self.user_id is None

    def apply(self, query_kwargs: dict) -> dict:
        if self.user_id:
            query_kwargs["assigned_to"] = self.user_id
        return query_kwargs


async def get_assigned_filter(
    user: User = Depends(get_current_user),
) -> AssignedFilter:
    if user.is_supervisor:
        return AssignedFilter(user_id=None)
    return AssignedFilter(user_id=user.id)


def require_roles(roles: list[str]):
    """Factory — lève 403 si le rôle de l'utilisateur n'est pas dans `roles`."""
    def _check(user: User = Depends(get_current_user)) -> User:
        if not user.a_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé pour votre rôle.",
            )
        return user
    return _check
