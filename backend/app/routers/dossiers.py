import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc, require_supervisor
from app.core.rbac import AssignedFilter
from app.models.user import User
from app.repositories import dossier_repo, audit_repo, user_repo
from pydantic import BaseModel
from app.models.dossier import CommentaireInterne
from app.schemas.kyc import DossierCreate, DossierOut


class CommentaireCreate(BaseModel):
    contenu: str


class CommentaireOut(BaseModel):
    id: str
    dossier_id: str
    user_id: str
    contenu: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_safe(cls, obj: CommentaireInterne) -> "CommentaireOut":
        return cls(
            id=obj.id,
            dossier_id=obj.dossier_id,
            user_id=obj.user_id,
            contenu=obj.contenu,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
        )

class AssignableUserOut(BaseModel):
    id: str
    full_name: str
    role: str


router = APIRouter(prefix="/dossiers", tags=["dossiers"])

_STATUTS_VALIDES = [
    "brouillon", "en_analyse", "vigilance_renforcee",
    "valide", "bloque", "traite", "cloture", "archive",
]

# Rôles pouvant se voir assigner un KYC / dossier : Notaire Principal et Clerc.
_ASSIGNABLE_ROLES = ("notaire_principal", "clercs")


def _ref() -> str:
    return f"DOS-{uuid.uuid4().hex[:8].upper()}"


@router.get("", response_model=list[DossierOut])
async def list_dossiers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    statut: str | None = Query(None),
    classification: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[DossierOut]:
    af = AssignedFilter(None if current_user.is_supervisor else current_user.id)
    filters = af.apply({})
    dossiers = await dossier_repo.list_dossiers(
        db,
        assigned_to=filters.get("assigned_to"),
        statut=statut,
        classification=classification,
        limit=limit,
        offset=offset,
    )
    return [DossierOut.model_validate(d) for d in dossiers]


@router.post("", response_model=DossierOut, status_code=status.HTTP_201_CREATED)
async def create_dossier(
    body: DossierCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    dossier = await dossier_repo.create(
        db,
        reference=_ref(),
        type_client=body.type_client,
        type_operation=body.type_operation,
        type_operation_detail=body.type_operation_detail,
        created_by=current_user.id,
        assigned_to=current_user.id if current_user.role == "clercs" else None,
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dossier.created",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier.id,
        ip=ip,
        detail={"reference": dossier.reference, "type_client": body.type_client},
    )
    return DossierOut.model_validate(dossier)


@router.get("/assignables", response_model=list[AssignableUserOut])
async def list_assignables(
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> list[AssignableUserOut]:
    """Utilisateurs assignables à un KYC / dossier : Notaire Principal + Clerc.

    Accessible aux superviseurs (admin, notaire_principal) — contrairement à
    GET /users réservé à l'admin.
    """
    users = await user_repo.get_all(db)
    return [
        AssignableUserOut(id=u.id, full_name=u.full_name, role=u.role)
        for u in users
        if u.is_active and u.role in _ASSIGNABLE_ROLES
    ]


@router.get("/{dossier_id}", response_model=DossierOut)
async def get_dossier(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    return DossierOut.model_validate(dossier)


@router.patch("/{dossier_id}/assign", response_model=DossierOut)
async def assign_dossier(
    dossier_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    target_user = await user_repo.get_by_id(db, user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur invalide.")
    if target_user.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul un Notaire Principal ou un Clerc peut se voir assigner un dossier.",
        )
    from sqlalchemy import update as sa_update
    from app.models.dossier import Dossier
    await db.execute(sa_update(Dossier).where(Dossier.id == dossier_id).values(assigned_to=user_id))
    await db.commit()
    await db.refresh(dossier)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dossier.assigned",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={"assigned_to": user_id},
    )
    return DossierOut.model_validate(dossier)


@router.patch("/{dossier_id}/statut", response_model=DossierOut)
async def change_statut(
    dossier_id: str,
    new_statut: str,
    commentaire: str | None = None,
    request: Request = None,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    if new_statut not in _STATUTS_VALIDES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Statut '{new_statut}' invalide.")
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    dossier = await dossier_repo.update_statut(db, dossier, new_statut, current_user.id, commentaire)
    ip = request.client.host if request and request.client else "unknown"
    await audit_repo.log(
        db,
        action="dossier.statut_change",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={"statut": new_statut, "commentaire": commentaire},
    )
    return DossierOut.model_validate(dossier)


@router.get("/{dossier_id}/commentaires", response_model=list[CommentaireOut])
async def list_commentaires(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommentaireOut]:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    from sqlalchemy import select
    result = await db.execute(
        select(CommentaireInterne)
        .where(CommentaireInterne.dossier_id == dossier_id)
        .order_by(CommentaireInterne.created_at.asc())
    )
    return [CommentaireOut.from_orm_safe(c) for c in result.scalars().all()]


@router.post("/{dossier_id}/commentaires", response_model=CommentaireOut, status_code=status.HTTP_201_CREATED)
async def add_commentaire_endpoint(
    dossier_id: str,
    body: CommentaireCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentaireOut:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    commentaire = await dossier_repo.add_commentaire(db, dossier_id, current_user.id, body.contenu)
    return CommentaireOut.from_orm_safe(commentaire)
