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


class UserCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    password: str = Field(..., min_length=12)
    must_change_password: bool = True

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    totp_enabled: bool
    requires_2fa: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
