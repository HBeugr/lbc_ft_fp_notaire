from pydantic import BaseModel
from typing import Literal

TypeAlerte = Literal["T1_PPE","T2_ESPECES","T3_SANCTIONS","T4_GAFI","T5_REFUS_DOC","T6_BE_NON_IDENTIFIABLE","INCOHERENCE_DOC","MONTAGE_COMPLEXE","AUTRE"]
NiveauAlerte = Literal["FAIBLE","MOYEN","ELEVE"]
StatutAlerte = Literal["ouverte","en_cours","traitee","ignoree"]


class AlerteCreate(BaseModel):
    dossier_id: str
    type_alerte: TypeAlerte
    niveau: NiveauAlerte
    description: str | None = None


class AlerteTraiter(BaseModel):
    statut: Literal["en_cours","traitee","ignoree"]
    resolution_note: str | None = None


class SignalementInterneRequest(BaseModel):
    description: str
    dossier_reference: str | None = None


class AlerteOut(BaseModel):
    id: str
    dossier_id: str | None
    type_alerte: str
    niveau: str
    statut: str
    description: str | None
    traite_par: str | None
    traite_at: str | None
    resolution_note: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_safe(cls, obj) -> "AlerteOut":
        return cls(
            id=obj.id,
            dossier_id=obj.dossier_id,
            type_alerte=obj.type_alerte,
            niveau=obj.niveau,
            statut=obj.statut,
            description=obj.description,
            traite_par=obj.traite_par,
            traite_at=obj.traite_at.isoformat() if obj.traite_at else None,
            resolution_note=obj.resolution_note,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
        )


class AlerteListResponse(BaseModel):
    items: list[AlerteOut]
    total: int
    page: int
    page_size: int
