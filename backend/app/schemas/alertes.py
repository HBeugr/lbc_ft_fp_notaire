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


# Mapping statut DB (minuscules) → contrat frontend (MAJUSCULES)
_STATUT_UP = {"ouverte": "OUVERTE", "en_cours": "EN_COURS", "traitee": "TRAITEE", "ignoree": "IGNOREE"}


class AlerteOut(BaseModel):
    id: str
    dossier_id: str | None
    dossier_reference: str | None = None
    dossier_statut: str | None = None
    type_alerte: str
    niveau: str
    statut: str
    description: str | None
    # Prise en charge (en_cours)
    prise_en_charge_par: str | None = None
    prise_en_charge_at: str | None = None
    # Traitement (nommage aligné frontend immo)
    justification_traitement: str | None = None
    traitee_par: str | None = None
    traitee_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_safe(cls, obj, *, dossier_reference: str | None = None, dossier_statut: str | None = None) -> "AlerteOut":
        return cls(
            id=obj.id,
            dossier_id=obj.dossier_id,
            dossier_reference=dossier_reference,
            dossier_statut=dossier_statut,
            type_alerte=obj.type_alerte,
            niveau=obj.niveau,
            statut=_STATUT_UP.get(obj.statut, (obj.statut or "").upper()),
            description=obj.description,
            prise_en_charge_par=getattr(obj, "prise_en_charge_par", None),
            prise_en_charge_at=obj.prise_en_charge_at.isoformat() if getattr(obj, "prise_en_charge_at", None) else None,
            justification_traitement=obj.resolution_note,
            traitee_par=obj.traite_par,
            traitee_at=obj.traite_at.isoformat() if obj.traite_at else None,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
        )


class AlerteListResponse(BaseModel):
    items: list[AlerteOut]
    total: int
    page: int
    page_size: int
