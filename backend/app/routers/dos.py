"""
Router DOS — Déclarations d'Opérations Suspectes.

Règles Art. 63 — Confidentialité absolue :
  - Aucun rôle ne peut révéler l'existence d'une DOS au client
  - Accès restreint : responsable_conformite + notaire_principal + admin (require_rc)
  - Le statut 'DOS en cours' sur le dossier ne doit pas apparaître dans les documents clients
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import require_rc
from app.models.dos import DeclarationSuspicion, DosAddendum
from app.models.user import User
from app.repositories import dos_repo, dossier_repo, audit_repo
from app.schemas.dos import AddendumCreate, AddendumOut, DosCreate, DosOut, DosUpsert

router = APIRouter(prefix="/dos", tags=["dos"])


def _ref() -> str:
    return f"DOS-{uuid.uuid4().hex[:10].upper()}"


async def _get_dos_or_404(db: AsyncSession, dos_id: str) -> DeclarationSuspicion:
    dos = await dos_repo.get_by_id(db, dos_id)
    if not dos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DOS introuvable.")
    return dos


async def _dos_with_addendums(db: AsyncSession, dos: DeclarationSuspicion) -> DosOut:
    result = await db.execute(
        select(DosAddendum).where(DosAddendum.dos_id == dos.id).order_by(DosAddendum.created_at)
    )
    return DosOut.from_orm_safe(dos, addendums=list(result.scalars().all()))


@router.get("", response_model=list[DosOut])
async def list_dos(
    _: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
    statut: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[DosOut]:
    dos_list = await dos_repo.list_all(db, limit=limit, offset=offset)
    if statut:
        dos_list = [d for d in dos_list if d.statut == statut]
    result = []
    for dos in dos_list:
        add_result = await db.execute(select(DosAddendum).where(DosAddendum.dos_id == dos.id))
        result.append(DosOut.from_orm_safe(dos, addendums=list(add_result.scalars().all())))
    return result


@router.post("", response_model=DosOut, status_code=status.HTTP_201_CREATED)
async def create_dos(
    body: DosCreate,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    dossier = await dossier_repo.get_by_id(db, body.dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    existing = await dos_repo.get_by_dossier(db, body.dossier_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une DOS existe déjà pour ce dossier.")
    dos = await dos_repo.create(
        db,
        dossier_id=body.dossier_id,
        reference_interne=_ref(),
        initie_par=current_user.id,
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.created",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos.id,
        ip=ip,
        detail={"reference": dos.reference_interne, "dossier_id": body.dossier_id},
    )
    return DosOut.from_orm_safe(dos)


@router.get("/{dos_id}", response_model=DosOut)
async def get_dos(
    dos_id: str,
    _: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    dos = await _get_dos_or_404(db, dos_id)
    return await _dos_with_addendums(db, dos)


@router.put("/{dos_id}", response_model=DosOut)
async def update_dos(
    dos_id: str,
    body: DosUpsert,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut == "soumis":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DOS déjà soumise — utiliser un addendum pour modifier."
        )
    data = body.model_dump(exclude_none=True)
    for field in ("motifs", "statut_operations", "supports", "relations_affaires"):
        if field in data and data[field] is not None and not isinstance(data[field], dict):
            data[field] = data[field].model_dump() if hasattr(data[field], "model_dump") else dict(data[field])
    if "detail_transactions" in data and isinstance(data["detail_transactions"], list):
        data["detail_transactions"] = [
            t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in data["detail_transactions"]
        ]
    dos = await dos_repo.update(db, dos, **data)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.updated",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos_id,
        ip=ip,
    )
    return await _dos_with_addendums(db, dos)


@router.post("/{dos_id}/soumettre", response_model=DosOut)
async def soumettre_dos(
    dos_id: str,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Soumet la DOS à la CENTIF — délai légal max 24h (Art. 2 §58)."""
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut == "soumis":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="DOS déjà soumise.")
    if not (dos.type_soupcon_bc or dos.type_soupcon_ft or dos.type_soupcon_prolif):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sélectionner au moins un type de soupçon avant de soumettre."
        )
    dos = await dos_repo.update(
        db, dos,
        statut="soumis",
        valide_par=current_user.id,
        soumis_at=datetime.now(timezone.utc),
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.soumis",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos_id,
        ip=ip,
        detail={"reference": dos.reference_interne},
    )
    return await _dos_with_addendums(db, dos)


@router.patch("/{dos_id}/accuse-recu", response_model=DosOut)
async def accuse_recu_dos(
    dos_id: str,
    reference_centif: str,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Enregistre l'accusé de réception CENTIF."""
    dos = await _get_dos_or_404(db, dos_id)
    dos = await dos_repo.update(
        db, dos,
        statut="accuse_recu",
        accuse_recu_ref=reference_centif,
        accuse_recu_at=datetime.now(timezone.utc),
    )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.accuse_recu",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos_id,
        ip=ip,
        detail={"reference_centif": reference_centif},
    )
    return await _dos_with_addendums(db, dos)


@router.post("/{dos_id}/addendums", response_model=AddendumOut, status_code=status.HTTP_201_CREATED)
async def add_addendum(
    dos_id: str,
    body: AddendumCreate,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> AddendumOut:
    """Complément d'information — append-only, même après soumission."""
    await _get_dos_or_404(db, dos_id)
    addendum = await dos_repo.add_addendum(db, dos_id, current_user.id, body.contenu)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.addendum_added",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos_id,
        ip=ip,
    )
    return AddendumOut.from_orm_safe(addendum)
