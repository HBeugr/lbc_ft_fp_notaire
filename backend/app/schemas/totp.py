from pydantic import BaseModel, Field


class TotpSetupResponse(BaseModel):
    provisioning_uri: str
    qr_data: str


class TotpActivateRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TotpVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TotpVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
