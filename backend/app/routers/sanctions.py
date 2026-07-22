"""Gestion des sanctions & criblage — reproduit la logique du projet assujetti.

  GET   /api/sanctions                 → listes actives (fraîcheur calculée)
  POST  /api/sanctions/upload          → import CSV / PDF / HTML (admin)
  POST  /api/sanctions/cribler         → criblage flou d'un nom (superviseur) + T3
  PATCH /api/sanctions/{id}/deactivate → désactivation soft (admin)
"""
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_supervisor
from app.models.dossier import Dossier
from app.models.user import User
from app.repositories import sanctions_repo, audit_repo, dossier_repo, alertes_repo
from app.schemas.sanction import (
    SanctionsListResponse, ListeSanctionsOut,
    CriblerIn, CriblageResponse, CriblageResult,
)
from app.services import sanctions_parser_service, sanctions_service

router = APIRouter(prefix="/sanctions", tags=["sanctions"])

_TYPES_VALIDES = {
    "GIABA", "BCEAO", "OFAC", "UE_CSDNU", "AUTRE",
    # Financement de la Prolifération (M1.2)
    "ONU_PROLIFERATION", "OFAC_WMD", "UE_PROLIFERATION", "CENTIF_FP",
}
# Types de listes relevant du Financement de la Prolifération
_TYPES_PROLIFERATION = {"ONU_PROLIFERATION", "OFAC_WMD", "UE_PROLIFERATION", "CENTIF_FP"}
_EXT_VALIDES = {".csv", ".pdf", ".html", ".htm"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 Mo


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _to_out(liste) -> ListeSanctionsOut:
    activated = liste.activated_at
    if activated and activated.tzinfo is None:
        activated = activated.replace(tzinfo=timezone.utc)
    age_jours = (datetime.now(timezone.utc) - activated).days if activated else 0
    return ListeSanctionsOut(
        id=liste.id,
        nom=liste.nom,
        type_liste=liste.type_liste,
        total_entrees=liste.total_entrees,
        activated_at=activated.isoformat() if activated else "",
        age_jours=age_jours,
        is_stale=age_jours > sanctions_service.SANCTIONS_THRESHOLD_DAYS,
    )


@router.get("", response_model=SanctionsListResponse)
async def list_sanctions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctionsListResponse:
    listes = await sanctions_repo.list_active(db)
    items = [_to_out(liste) for liste in listes]
    return SanctionsListResponse(items=items, total=len(items))


@router.post("/upload", response_model=ListeSanctionsOut, status_code=status.HTTP_201_CREATED)
async def upload_sanctions(
    request: Request,
    nom: str = Form(...),
    type_liste: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ListeSanctionsOut:
    if type_liste not in _TYPES_VALIDES:
        raise HTTPException(status_code=422, detail="Type de liste invalide.")

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 10 Mo).")

    safe_filename = os.path.basename(file.filename or "")
    ext = Path(safe_filename).suffix.lower()
    if ext not in _EXT_VALIDES:
        raise HTTPException(
            status_code=422,
            detail=f"Format non supporté : '{ext or '(aucune extension)'}'. Formats acceptés : .csv, .pdf, .html",
        )

    entries = sanctions_parser_service.detect_and_parse(safe_filename, content)
    if not entries:
        raise HTTPException(
            status_code=422,
            detail="Aucune entrée exploitable extraite du fichier. "
                   "Vérifiez que le format correspond à une liste de sanctions reconnue (ONU HTML, 1373 PDF, CSV).",
        )

    liste = await sanctions_repo.create_liste(
        db, nom=nom, type_liste=type_liste, uploaded_by=current_user.id, entries=entries,
    )
    await audit_repo.log(
        db,
        action="sanctions.liste_uploadee",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="liste_sanctions",
        entity_id=liste.id,
        ip=_ip(request),
        detail={"nom": nom, "type_liste": type_liste, "total_entrees": liste.total_entrees},
    )
    return _to_out(liste)


@router.post("/cribler", response_model=CriblageResponse)
async def cribler(
    body: CriblerIn,
    request: Request,
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> CriblageResponse:
    listes = await sanctions_repo.get_active_with_entries(db)
    raw_results = sanctions_service.screen(
        nom=body.nom,
        date_naissance=body.date_naissance,
        lieu_naissance=body.lieu_naissance,
        seuil=body.seuil,
        listes=listes,
    )
    has_match = any(r["statut"] == "match" for r in raw_results)

    await audit_repo.log(
        db,
        action="sanctions.criblage",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="criblage",
        entity_id=body.dossier_id or "standalone",
        ip=_ip(request),
        detail={"nom_crible": body.nom, "has_match": has_match,
                "matches": [r["liste"] for r in raw_results if r["statut"] == "match"]},
    )

    # T3 absolutoire — blocage immédiat (Art. 89) si dossier rattaché + correspondance
    if has_match and body.dossier_id:
        dossier = await dossier_repo.get_by_id(db, body.dossier_id)
        if dossier:
            await db.execute(
                sa_update(Dossier).where(Dossier.id == dossier.id).values(
                    trigger_actif="T3", classification="ELEVE",
                    force_par_trigger=True, statut="bloque",
                )
            )
            best = next(r for r in raw_results if r["statut"] == "match")
            # Anti-doublon : ne pas réempiler si une alerte T3 active existe déjà sur le dossier.
            if not await alertes_repo.exists_active(db, dossier_id=dossier.id, type_alerte="T3_SANCTIONS"):
                await alertes_repo.create(
                    db,
                    dossier_id=dossier.id,
                    type_alerte="T3_SANCTIONS",
                    niveau="ELEVE",
                    statut="ouverte",
                    description=(
                        f"Correspondance sanctions : « {body.nom} » ≈ « {best['nom_correspondant']} » "
                        f"(score {best['score']}%) — liste {best['liste']}. Trigger T3, blocage Art. 89."
                    ),
                )
            await db.commit()

    return CriblageResponse(
        nom_crible=body.nom,
        has_match=has_match,
        results=[CriblageResult(**r) for r in raw_results],
    )


@router.patch("/{liste_id}/deactivate")
async def deactivate_sanctions(
    liste_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    liste = await sanctions_repo.get_by_id(db, liste_id)
    if not liste:
        raise HTTPException(status_code=404, detail="Liste introuvable.")
    if not liste.is_active:
        raise HTTPException(status_code=409, detail="La liste est déjà inactive.")
    await sanctions_repo.deactivate(db, liste)
    await audit_repo.log(
        db,
        action="sanctions.liste_desactivee",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="liste_sanctions",
        entity_id=liste.id,
        ip=_ip(request),
        detail={"nom": liste.nom},
    )
    return {"status": "ok"}


@router.post("/check-freshness")
async def check_freshness(
    request: Request,
    current_user: User = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Contrôle de fraîcheur des listes actives : génère une alerte SANCTIONS_PERIMEES
    si au moins une liste dépasse le seuil (> 95 j). Destiné à un cron externe
    (le notaire n'a pas de scheduler in-process)."""
    from sqlalchemy import select as _sel, func as _func
    from app.models.sanction import ListeSanctions
    from app.models.alerte import Alerte
    now = datetime.now(timezone.utc)
    threshold = sanctions_service.SANCTIONS_THRESHOLD_DAYS
    listes = (await db.execute(_sel(ListeSanctions).where(ListeSanctions.is_active.is_(True)))).scalars().all()

    def _age_days(activated) -> int:
        if not activated:
            return 0
        # PostgreSQL renvoie des datetimes conscients du fuseau (TIMESTAMPTZ) ;
        # le repli couvre les valeurs naïves héritées de la reprise MySQL.
        if activated.tzinfo is None:
            activated = activated.replace(tzinfo=timezone.utc)
        return (now - activated).days

    stale = [l for l in listes if _age_days(l.activated_at) > threshold]
    if not stale:
        return {"stale": 0, "alerte_creee": False}
    # Anti-doublon : une seule alerte SANCTIONS_PERIMEES active à la fois.
    actives = (await db.execute(_sel(_func.count(Alerte.id)).where(
        Alerte.type_alerte == "SANCTIONS_PERIMEES", Alerte.statut.in_(("ouverte", "en_cours"))
    ))).scalar_one()
    creee = False
    if not actives:
        noms = ", ".join(l.nom for l in stale[:5])
        await alertes_repo.create(
            db, dossier_id=None, type_alerte="SANCTIONS_PERIMEES", niveau="ELEVE", statut="ouverte",
            description=f"{len(stale)} liste(s) de sanctions périmée(s) (> {threshold} j) : {noms}. Mise à jour requise.",
        )
        creee = True
        await audit_repo.log(
            db, action="sanctions.perimees_alerte", user_id=current_user.id, user_role=current_user.role,
            entity_type="liste_sanctions", entity_id="freshness", ip=_ip(request), detail={"stale": len(stale)},
        )
    return {"stale": len(stale), "alerte_creee": creee}
