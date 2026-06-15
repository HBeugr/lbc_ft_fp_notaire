import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc, require_supervisor
from app.core.rbac import AssignedFilter
from app.models.user import User
from app.repositories import dossier_repo, audit_repo, user_repo, alertes_repo
from pydantic import BaseModel
from app.models.dossier import CommentaireInterne
from app.schemas.kyc import DossierCreate, DossierOut, DossierTransactionRequest


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
    return f"KYC-{uuid.uuid4().hex[:8].upper()}"


class DossierListOut(BaseModel):
    items: list[DossierOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=DossierListOut)
async def list_dossiers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    statut: str | None = Query(None),
    classification: str | None = Query(None),
    reference: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> DossierListOut:
    af = AssignedFilter(None if current_user.is_supervisor else current_user.id)
    assigned_to = af.apply({}).get("assigned_to")
    common = dict(
        assigned_to=assigned_to, statut=statut,
        classification=classification, reference=reference,
    )
    total = await dossier_repo.count_dossiers(db, **common)
    dossiers = await dossier_repo.list_dossiers(
        db, **common, limit=page_size, offset=(page - 1) * page_size,
    )
    return DossierListOut(
        items=[DossierOut.model_validate(d) for d in dossiers],
        total=total, page=page, page_size=page_size,
    )


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
    # Re-fetch avec eager-load des relations KYC (évite MissingGreenlet à la sérialisation)
    dossier = await dossier_repo.get_by_id(db, dossier.id)
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


async def _serialize_dossier(db: AsyncSession, dossier) -> DossierOut:
    """DossierOut + résolution du nom de l'agent assigné."""
    out = DossierOut.model_validate(dossier)
    if dossier.assigned_to:
        u = await user_repo.get_by_id(db, dossier.assigned_to)
        if u:
            out.assigned_to_name = getattr(u, "full_name", None) or f"{u.first_name} {u.last_name}".strip()
    return out


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
    return await _serialize_dossier(db, dossier)


_SEUIL_ESPECE = 15_000_000


@router.patch("/{dossier_id}/transaction", response_model=DossierOut)
async def update_transaction(
    dossier_id: str,
    body: DossierTransactionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    """Étape Transaction du KYC — montant (tranche + exact) et mode de paiement.
    Espèces > 15M FCFA → déclaration systématique de transaction en espèces (opération à surveiller)."""
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")

    dossier.montant_tranche = body.montant_tranche
    if body.montant_transaction is not None:
        dossier.montant_transaction = body.montant_transaction
    if body.mode_paiement is not None:
        dossier.mode_paiement = body.mode_paiement
    montant = float(body.montant_transaction or dossier.montant_transaction or 0)
    depasse_seuil = dossier.montant_tranche == "plus_15m" or montant > _SEUIL_ESPECE
    dossier.surveillance_espece = bool(dossier.mode_paiement == "especes" and depasse_seuil)

    # ── Auto-trigger espèces T2 (Art. 72) — sans attendre le scoring ─────────────
    # Espèces + (> 15M FCFA ou tranche plus_15m) → trigger T2 absolutoire, classification ÉLEVÉ.
    candidat = "T2" if (dossier.mode_paiement == "especes" and depasse_seuil) else None
    ancien = dossier.trigger_actif or ""
    deja_score = dossier.score_base is not None
    if candidat == "T2":
        if ancien != "T2":
            dossier.trigger_actif = "T2"
            dossier.classification = "ELEVE"
            dossier.force_par_trigger = True
    elif not deja_score and ancien == "T2":
        # plus d'espèces qualifiante + dossier non scoré → le trigger espèces auto disparaît
        dossier.trigger_actif = None
        dossier.classification = None
        dossier.force_par_trigger = False

    nouveau = dossier.trigger_actif or ""
    await db.commit()
    await db.refresh(dossier)

    # Alertes : créer l'alerte T2_ESPECES (anti-doublon) ou résoudre l'ancienne si le trigger a disparu
    existantes = await alertes_repo.list_alertes(db, type_alerte="T2_ESPECES", dossier_id=dossier_id, limit=50)
    ouvertes_t2 = [a for a in existantes[0] if a.statut in ("ouverte", "en_cours")]
    if nouveau == "T2":
        if not ouvertes_t2:
            await alertes_repo.create(
                db, dossier_id=dossier_id, type_alerte="T2_ESPECES", niveau="ELEVE", statut="ouverte",
                description=f"Trigger T2 (espèces > 15M FCFA, Art. 72) déclenché sur le dossier {dossier.reference}.",
            )
    elif ancien == "T2" and nouveau != "T2":
        for a in ouvertes_t2:
            await alertes_repo.update_statut(db, a, statut="traitee", traite_par=current_user.id,
                                             note="Trigger T2 retiré — transaction corrigée (mode/montant).")

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="dossier.transaction_saved", user_id=current_user.id, user_role=current_user.role,
        entity_type="dossier", entity_id=dossier_id, ip=ip,
        detail={"montant_tranche": body.montant_tranche, "mode_paiement": body.mode_paiement,
                "surveillance_espece": dossier.surveillance_espece, "trigger_actif": dossier.trigger_actif},
    )
    return await _serialize_dossier(db, dossier)


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
    # WRK-04 — la clôture (et l'archivage) est réservée à l'Admin et au Notaire Principal (séparation Art. 12)
    if new_statut in ("cloture", "archive") and current_user.role not in ("admin", "notaire_principal"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La clôture d'un dossier est réservée au Notaire Principal et à l'Administrateur.",
        )
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
