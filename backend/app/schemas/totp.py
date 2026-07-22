from pydantic import BaseModel, Field


class TotpSetupResponse(BaseModel):
    provisioning_uri: str
    qr_data: str


class TotpActivateRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TotpActivateResponse(BaseModel):
    # Codes de secours affichés UNE SEULE FOIS à l'activation
    backup_codes: list[str]


class TotpVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TotpBackupVerifyRequest(BaseModel):
    # Code de secours (hex, tirets/espaces tolérés)
    code: str = Field(..., min_length=6, max_length=40)


class TotpVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TotpBackupCodesResponse(BaseModel):
    backup_codes: list[str]
