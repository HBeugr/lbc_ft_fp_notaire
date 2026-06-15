from pydantic import BaseModel, EmailStr, Field
from typing import Literal


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
    password: str = Field(..., min_length=8)
    must_change_password: bool = True


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
