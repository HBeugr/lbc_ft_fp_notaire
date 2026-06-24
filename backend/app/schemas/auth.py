from pydantic import BaseModel, Field, field_validator

from app.core.password_policy import validate_password_strength


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    totp_enabled: bool
    requires_2fa: bool
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    totp_pending: bool = False


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)
