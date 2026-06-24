import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc, require_supervisor
from app.core.rbac import AssignedFilter
from app.core import runtime_config
from app.models.user import User
from app.repositories import dossier_repo, audit_repo, user_repo, alertes_repo
from pydantic import BaseModel
from app.models.dossier import CommentaireInterne, KycBE
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

# ── Gouvernance des transitions de statut (matrice + RBAC + garde-fous) ────────
_TRANSITIONS: dict[str, set[str]] = {
    "brouillon":           {"en_analyse"},
    "en_analyse":          {"vigilance_renforcee", "valide", "bloque", "brouillon"},
    "vigilance_renforcee": {"valide", "bloque"},
    "valide":              {"traite", "bloque"},
    "bloque":              {"en_analyse"},
    "traite":              {"cloture"},
    "cloture":             {"archive"},
    "archive":             set(),
}

# Rôles notaire. RC = responsable_conformite ; Notaire Principal = Dirigeant ; clercs/autre = opérationnels.
_OPERATIONNELS = frozenset({"clercs", "autre_utilisateur"})
_CONFORMITE = frozenset({"responsable_conformite", "notaire_principal", "admin"})
_CLOTURE = frozenset({"notaire_principal", "admin"})  # WRK-04 — séparation Art. 12
_ALL_ROLES = _OPERATIONNELS | _CONFORMITE

_TRANSITION_ROLES: dict[tuple[str, str], frozenset[str]] = {
    ("brouillon",           "en_analyse"):          _ALL_ROLES,
    ("en_analyse",          "brouillon"):           _CONFORMITE,
    ("en_analyse",          "vigilance_renforcee"): _CONFORMITE,
    ("en_analyse",          "valide"):              _CONFORMITE,
    ("en_analyse",          "bloque"):              _CONFORMITE,
    ("vigilance_renforcee", "valide"):              _CONFORMITE,
    ("vigilance_renforcee", "bloque"):              _CONFORMITE,
    ("valide",              "traite"):              _CONFORMITE,
    ("valide",              "bloque"):              _CONFORMITE,
    ("bloque",              "en_analyse"):          _CONFORMITE,
    ("traite",              "cloture"):             _CLOTURE,
    ("cloture",             "archive"):             _CLOTURE,
}

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
    search: str | None = Query(None, description="Recherche libre : référence ou nom du client"),
    mine: bool = Query(False, description="Superviseur : limiter aux dossiers qui me sont assignés"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> DossierListOut:
    # Opérationnel : toujours ses dossiers. Superviseur : tous, ou seulement les siens si mine=true.
    if current_user.is_supervisor:
        assigned_to = current_user.id if mine else None
    else:
        assigned_to = current_user.id
    common = dict(
        assigned_to=assigned_to, statut=statut,
        classification=classification, reference=reference, search=search,
    )
    total = await dossier_repo.count_dossiers(db, **common)
    dossiers = await dossier_repo.list_dossiers(
        db, **common, limit=page_size, offset=(page - 1) * page_size,
    )
    items = [DossierOut.model_validate(d) for d in dossiers]
    # Peuplement du nom de l'assigné (fetch groupé)
    assigned_ids = {d.assigned_to for d in dossiers if d.assigned_to}
    if assigned_ids:
        from sqlalchemy import select as _select
        rows = (await db.execute(_select(User).where(User.id.in_(assigned_ids)))).scalars().all()
        name_map = {
            u.id: (getattr(u, "full_name", None) or f"{u.first_name} {u.last_name}".strip())
            for u in rows
        }
        for o in items:
            if o.assigned_to:
                o.assigned_to_name = name_map.get(o.assigned_to)
    return DossierListOut(
        items=items, total=total, page=page, page_size=page_size,
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


# Seuil espèces (Art. 72, T2) — désormais configurable par l'Admin (cf. runtime_config).


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
    depasse_seuil = dossier.montant_tranche == "plus_15m" or montant > runtime_config.get_seuil_especes_t2()
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    if new_statut not in _STATUTS_VALIDES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Statut '{new_statut}' invalide.")
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")

    # 1. Graphe de transitions autorisées
    if new_statut not in _TRANSITIONS.get(dossier.statut, set()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transition '{dossier.statut}' → '{new_statut}' non autorisée.",
        )
    # 2. RBAC par paire (from, to)
    allowed_roles = _TRANSITION_ROLES.get((dossier.statut, new_statut), frozenset())
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Votre rôle ne permet pas cette transition.")
    # 3. WRK-09 — un dossier PPE (Trigger T1, Art. 29) ne peut être validé que par le Notaire Principal
    if new_statut == "valide" and dossier.trigger_actif == "T1" and current_user.role != "notaire_principal":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dossier PPE (Trigger T1, Art. 29) — la validation requiert le Notaire Principal (WRK-09).",
        )
    # 4. Garde-fou BE (Art. 17) — une Personne Morale requiert ≥1 BE validé avant validation
    if new_statut == "valide" and dossier.type_client == "PM":
        kyc_pm = await dossier_repo.get_kyc_pm(db, dossier_id)
        be_valides = 0
        if kyc_pm:
            from sqlalchemy import select as _sel, func as _func
            be_valides = (await db.execute(
                _sel(_func.count(KycBE.id)).where(KycBE.kyc_pm_id == kyc_pm.id, KycBE.statut_validation == "valide")
            )).scalar_one()
        if not be_valides:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Validation impossible : une Personne Morale requiert au moins un bénéficiaire effectif validé (Art. 17).",
            )
    # 5. Garde-fou alerte — pas de validation avec une alerte ÉLEVÉ non traitée
    if new_statut == "valide":
        nb = await alertes_repo.count_non_traitees_critiques(db, dossier_id)
        if nb > 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation impossible : {nb} alerte(s) ÉLEVÉ non traitée(s) sur ce dossier. Traitez-les d'abord.",
            )
    # 6. Commentaire obligatoire (sauf soumission brouillon → en_analyse)
    if dossier.statut != "brouillon" and not (commentaire and commentaire.strip()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Un commentaire est obligatoire pour cette transition.")

    dossier = await dossier_repo.update_statut(db, dossier, new_statut, current_user.id, commentaire)

    # Auto-planification d'une révision périodique à la validation (fréquence selon le
    # niveau de risque) — sans elle, l'escalade J+30/60/90/120 ne s'enclencherait jamais.
    if new_statut == "valide":
        from app.models.revision import RevisionKyc
        from app.services import revision_service
        from sqlalchemy import select as _sel, func as _func
        existe = (await db.execute(
            _sel(_func.count(RevisionKyc.id)).where(
                RevisionKyc.dossier_id == dossier_id,
                RevisionKyc.statut.notin_(("completee",)),
            )
        )).scalar_one()
        if not existe:
            echeance = revision_service.prochaine_echeance(
                dossier.classification or "MOYEN",
                est_ppe=(dossier.trigger_actif == "T1"),
                trigger_actif=bool(dossier.trigger_actif),
            )
            db.add(RevisionKyc(
                dossier_id=dossier_id, date_echeance=echeance,
                classification_avant=dossier.classification, score_avant=dossier.score_base,
            ))
            await db.commit()

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


class TriggerManuelRequest(BaseModel):
    trigger: str
    commentaire: str | None = None


_MANUAL_TRIGGERS = {
    "T5": ("T5_REFUS_DOC", "Refus documentaire (Art. 25)"),
    "T6": ("T6_BE_NON_IDENTIFIABLE", "Bénéficiaire effectif non identifiable (Art. 17)"),
}


@router.post("/{dossier_id}/trigger-manuel", response_model=DossierOut)
async def declencher_trigger_manuel(
    dossier_id: str,
    body: TriggerManuelRequest,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    """Déclenchement manuel d'un trigger absolutoire T5/T6 (RC/Notaire Principal/Admin).
    Force la classification ÉLEVÉ + crée l'alerte correspondante (anti-doublon)."""
    spec = _MANUAL_TRIGGERS.get(body.trigger)
    if not spec:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Trigger non autorisé manuellement (valeurs : T5, T6).")
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    type_alerte, motif = spec
    dossier.trigger_actif = body.trigger
    dossier.classification = "ELEVE"
    dossier.force_par_trigger = True
    db.add(dossier)
    await db.commit()
    if not await alertes_repo.exists_active(db, dossier_id=dossier_id, type_alerte=type_alerte):
        desc = f"Trigger {body.trigger} déclenché manuellement — {motif}."
        if body.commentaire:
            desc += f" {body.commentaire.strip()}"
        await alertes_repo.create(db, dossier_id=dossier_id, type_alerte=type_alerte,
                                  niveau="ELEVE", statut="ouverte", description=desc)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="dossier.trigger_manuel", user_id=current_user.id, user_role=current_user.role,
        entity_type="dossier", entity_id=dossier_id, ip=ip,
        detail={"trigger": body.trigger, "commentaire": body.commentaire},
    )
    dossier = await dossier_repo.get_by_id(db, dossier_id)  # re-fetch eager-loadé (évite MissingGreenlet)
    return await _serialize_dossier(db, dossier)


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


@router.get("/{dossier_id}/alertes")
async def list_dossier_alertes(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Alertes liées à un dossier (pour la fiche KYC) — ouvertes, en cours, traitées."""
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    alertes = await alertes_repo.get_by_dossier(db, dossier_id)
    return [
        {
            "id": a.id,
            "type_alerte": a.type_alerte,
            "niveau": a.niveau,
            "statut": a.statut,
            "description": a.description,
            "resolution_note": a.resolution_note,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alertes
    ]


@router.get("/{dossier_id}/historique")
async def get_historique(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Historique du cycle de vie d'un dossier (append-only)."""
    from sqlalchemy import select
    from app.models.dossier import DossierHistorique

    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    result = await db.execute(
        select(DossierHistorique)
        .where(DossierHistorique.dossier_id == dossier_id)
        .order_by(DossierHistorique.created_at.asc())
    )
    return [
        {
            "id": h.id,
            "dossier_id": h.dossier_id,
            "action": f"{h.statut_avant} → {h.statut_apres}" if h.statut_avant else h.statut_apres,
            "user_id": h.user_id,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "detail": {"commentaire": h.commentaire} if h.commentaire else None,
        }
        for h in result.scalars().all()
    ]
