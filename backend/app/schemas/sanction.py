from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

TypeListe = Literal["GIABA", "BCEAO", "OFAC", "UE_CSDNU", "AUTRE"]


class ListeSanctionsOut(BaseModel):
    id: str
    nom: str
    type_liste: str
    total_entrees: int
    activated_at: str
    age_jours: int
    is_stale: bool


class SanctionsListResponse(BaseModel):
    items: list[ListeSanctionsOut]
    total: int


class CriblerIn(BaseModel):
    nom: str = Field(..., min_length=1)
    date_naissance: str | None = None
    lieu_naissance: str | None = None
    dossier_id: str | None = None
    seuil: float = Field(85.0, ge=0, le=100)


class CriblageResult(BaseModel):
    liste: str
    type_liste: str
    score: int
    statut: str
    niveau: str
    ddn_detail: str | None = None
    nom_correspondant: str | None = None


class CriblageResponse(BaseModel):
    nom_crible: str
    has_match: bool
    results: list[CriblageResult]
