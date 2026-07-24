from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal

from app.core.password_policy import validate_password_strength


UserRole = Literal[
    "admin",
    "notaire_principal",
    "responsable_conformite",
    "clercs",
    "declarant_centif",
    "autre_utilisateur",
]


def _normaliser_cumul(roles: list[str]) -> list[str]:
    """Dédoublonne les rôles cumulés en conservant l'ordre de saisie.

    Le rôle principal n'est PAS retiré ici : seul le routeur connaît la valeur
    finalement retenue (création vs mise à jour partielle).
    """
    return list(dict.fromkeys(r for r in roles if r))


class UserCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    # Rôles CUMULÉS en plus du principal : une même personne, un seul compte.
    roles_extra: list[UserRole] = []
    password: str = Field(..., min_length=12)
    must_change_password: bool = True

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("roles_extra")
    @classmethod
    def _cumul_propre(cls, v: list[str]) -> list[str]:
        return _normaliser_cumul(v)


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    role: UserRole | None = None
    roles_extra: list[UserRole] | None = None
    is_active: bool | None = None

    @field_validator("roles_extra")
    @classmethod
    def _cumul_propre(cls, v: list[str] | None) -> list[str] | None:
        return _normaliser_cumul(v) if v is not None else v


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    # Tous les rôles détenus, principal en tête — toujours renseigné.
    roles: list[str] = []
    is_active: bool
    totp_enabled: bool
    requires_2fa: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
