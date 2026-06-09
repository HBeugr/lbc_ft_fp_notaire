from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc, require_supervisor
from app.models.user import User
from app.models.revision import RevisionKyc
from app.repositories import revision_repo, dossier_repo, audit_repo

router = APIRouter(prefix="/revisions", tags=["revisions"])

_STATUTS_VALIDES = ["planifiee", "en_cours", "completee", "en_retard", "vigilance_renforcee", "bloquee"]


class RevisionCreate(BaseModel):
    dossier_id: str
    date_echeance: str
    assigned_to: str | None = None


class RevisionUpdate(BaseModel):
    statut: str | None = None
    justification: str | None = None
    documents_mis_a_jour: str | None = None
    assigned_to: str | None = None
    date_relance_1: str | None = None
    date_relance_2: str | None = None


class RevisionOut(BaseModel):
    id: str
    dossier_id: str
    statut: str
    date_echeance: str
    date_relance_1: str | None
    date_relance_2: str | None
    date_validation: str | None
    classification_avant: str | None
    classification_apres: str | None
    score_avant: int | None
    score_apres: int | None
    assigned_to: str | None
    valide_par: str | None
    justification: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_safe(cls, r: RevisionKyc) -> "RevisionOut":
        def _d(v: object) -> str | None:
            if v is None:
                return None
            if isinstance(v, datetime):
                return v.isoformat()
            if isinstance(v, date):
                return v.isoformat()
            return str(v)

        return cls(
            id=r.id,
            dossier_id=r.dossier_id,
            statut=r.statut,
            date_echeance=_d(r.date_echeance) or "",
            date_relance_1=_d(r.date_relance_1),
            date_relance_2=_d(r.date_relance_2),
            date_validation=_d(r.date_validation),
            classification_avant=r.classification_avant,
            classification_apres=r.classification_apres,
            score_avant=r.score_avant,
            score_apres=r.score_apres,
            assigned_to=r.assigned_to,
            valide_par=r.valide_par,
            justification=r.justification,
            created_at=_d(r.created_at) or "",
        )


@router.get("", response_model=list[RevisionOut])
async def list_revisions(
    statut: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> list[RevisionOut]:
    from sqlalchemy import select
    q = select(RevisionKyc).order_by(RevisionKyc.date_echeance)
    if statut:
        q = q.where(RevisionKyc.statut == statut)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [RevisionOut.from_orm_safe(r) for r in result.scalars().all()]


@router.get("/a-venir", response_model=list[RevisionOut])
async def revisions_a_venir(
    jours: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> list[RevisionOut]:
    items = await revision_repo.list_a_venir(db, jours=jours)
    return [RevisionOut.from_orm_safe(r) for r in items]


@router.get("/en-retard", response_model=list[RevisionOut])
async def revisions_en_retard(
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> list[RevisionOut]:
    items = await revision_repo.list_en_retard(db)
    return [RevisionOut.from_orm_safe(r) for r in items]


@router.get("/{revision_id}", response_model=RevisionOut)
async def get_revision(
    revision_id: str,
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> RevisionOut:
    r = await revision_repo.get_by_id(db, revision_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Révision introuvable.")
    return RevisionOut.from_orm_safe(r)


@router.post("", response_model=RevisionOut, status_code=status.HTTP_201_CREATED)
async def create_revision(
    body: RevisionCreate,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> RevisionOut:
    dossier = await dossier_repo.get_by_id(db, body.dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    try:
        echeance = date.fromisoformat(body.date_echeance)
    except ValueError:
        raise HTTPException(status_code=422, detail="Format date invalide (YYYY-MM-DD).")
    r = await revision_repo.create(
        db,
        dossier_id=body.dossier_id,
        date_echeance=echeance,
        classification_avant=dossier.classification,
        score_avant=dossier.score_base,
        assigned_to=body.assigned_to,
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="revision.created",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="revision_kyc",
        entity_id=r.id,
        ip=ip,
        detail={"dossier_id": body.dossier_id, "date_echeance": body.date_echeance},
    )
    return RevisionOut.from_orm_safe(r)


@router.patch("/{revision_id}", response_model=RevisionOut)
async def update_revision(
    revision_id: str,
    body: RevisionUpdate,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> RevisionOut:
    r = await revision_repo.get_by_id(db, revision_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Révision introuvable.")
    if body.statut and body.statut not in _STATUTS_VALIDES:
        raise HTTPException(status_code=422, detail=f"Statut '{body.statut}' invalide.")
    kwargs: dict = {}
    if body.statut:
        kwargs["statut"] = body.statut
    if body.justification is not None:
        kwargs["justification"] = body.justification
    if body.documents_mis_a_jour is not None:
        kwargs["documents_mis_a_jour"] = body.documents_mis_a_jour
    if body.assigned_to is not None:
        kwargs["assigned_to"] = body.assigned_to
    if body.date_relance_1:
        kwargs["date_relance_1"] = date.fromisoformat(body.date_relance_1)
    if body.date_relance_2:
        kwargs["date_relance_2"] = date.fromisoformat(body.date_relance_2)
    r = await revision_repo.update(db, r, **kwargs)
    return RevisionOut.from_orm_safe(r)


@router.post("/{revision_id}/valider", response_model=RevisionOut)
async def valider_revision(
    revision_id: str,
    body: dict,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> RevisionOut:
    r = await revision_repo.get_by_id(db, revision_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Révision introuvable.")
    dossier = await dossier_repo.get_by_id(db, r.dossier_id)
    r = await revision_repo.update(
        db, r,
        statut="completee",
        date_validation=date.today(),
        valide_par=current_user.id,
        classification_apres=dossier.classification if dossier else r.classification_avant,
        score_apres=dossier.score_base if dossier else r.score_avant,
        justification=body.get("justification"),
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="revision.validee",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="revision_kyc",
        entity_id=revision_id,
        ip=ip,
        detail={"dossier_id": r.dossier_id, "classification_apres": r.classification_apres},
    )
    return RevisionOut.from_orm_safe(r)
