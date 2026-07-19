from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete, update as sa_update

from app.core import archivage
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.dossier import Dossier, KycBE, KycPPE, KycActionnaire
from app.repositories import dossier_repo, audit_repo, alertes_repo, sanctions_repo
from app.schemas.kyc import (
    KycPPUpsert, KycPPOut,
    KycPMUpsert, KycPMOut,
    KycBECreate, KycBEUpdate, KycBEOut,
    KycActCreate, KycActOut,
    KycPPECreate, KycPPEOut, KycPPEUpdate,
)
from app.routers.scoring import recompute_cache
from app.services import sanctions_service

router = APIRouter(prefix="/dossiers", tags=["kyc"])

_SANCTIONS_BLOCKED_DETAIL = (
    "Correspondance liste de sanctions confirmée (nom + date de naissance). "
    "Dossier bloqué — Trigger T3 absolutoire (Art. 89). Saisie d'une DOS requise."
)


async def _check_sanctions_on_save(
    db: AsyncSession,
    *,
    current_user: User,
    ip: str,
    dossier: Dossier,
    nom: str,
    date_naissance=None,
    lieu_naissance: str | None = None,
    nationalite: str | None = None,
) -> None:
    """Criblage formel au save du KYC — logique assujetti.

    blocked → T3 absolutoire (ÉLEVÉ + bloqué) + alerte + HTTP 422.
    warning → save autorisé, alerte RC + passage en_analyse.
    clear / no_lists → rien. Best-effort : une erreur de criblage ne bloque jamais
    la sauvegarde (sauf le blocage T3 intentionnel).
    """
    if not nom or len(nom.strip()) < 3:
        return
    try:
        listes = await sanctions_repo.get_active_with_entries(db)
        result = sanctions_service.pre_check(
            nom=nom, date_naissance=date_naissance,
            lieu_naissance=lieu_naissance, nationalite=nationalite, listes=listes,
        )
    except Exception:
        return  # criblage best-effort

    # Financement de la Prolifération (M1.2) — escalade en alerte dédiée
    _PROLIF = {"ONU_PROLIFERATION", "OFAC_WMD", "UE_PROLIFERATION", "CENTIF_FP"}
    is_prolif = result.get("type_liste") in _PROLIF
    type_alerte = "PROLIFERATION_MATCH" if is_prolif else "T3_SANCTIONS"
    motif_prolif = " Financement de la prolifération (M1.2)." if is_prolif else ""

    level = result["level"]
    if level == "blocked":
        await db.execute(
            sa_update(Dossier).where(Dossier.id == dossier.id).values(
                trigger_actif="T3", classification="ELEVE",
                force_par_trigger=True, statut="bloque",
            )
        )
        # Anti-doublon : le criblage est rejoué à chaque sauvegarde du dossier.
        if not await alertes_repo.exists_active(db, dossier_id=dossier.id, type_alerte=type_alerte):
            await alertes_repo.create(
                db, dossier_id=dossier.id, type_alerte=type_alerte,
                niveau="ELEVE", statut="ouverte",
                description=(
                    f"Correspondance sanctions confirmée (score {result['score']}%) — "
                    f"liste {result['liste']}. Trigger T3, blocage Art. 89.{motif_prolif}"
                ),
            )
        await audit_repo.log(
            db, action="sanctions.t3_active", user_id=current_user.id,
            user_role=current_user.role, entity_type="dossier", entity_id=dossier.id,
            ip=ip, detail={"liste": result["liste"], "score": result["score"]},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_SANCTIONS_BLOCKED_DETAIL)

    if level == "warning":
        try:
            # Anti-doublon : ne pas réempiler à chaque sauvegarde si une alerte active du même type existe.
            if not await alertes_repo.exists_active(db, dossier_id=dossier.id, type_alerte=type_alerte):
                await alertes_repo.create(
                    db, dossier_id=dossier.id, type_alerte=type_alerte,
                    niveau="MOYEN", statut="ouverte",
                    description=(
                        f"Correspondance partielle sanctions (score {result['score']}%) — "
                        f"liste {result['liste']}. Date de naissance non confirmée — vérification RC requise.{motif_prolif}"
                    ),
                )
            if dossier.statut == "brouillon":
                await db.execute(
                    sa_update(Dossier).where(Dossier.id == dossier.id).values(statut="en_analyse")
                )
            await db.commit()
        except Exception:
            pass


# États à partir desquels la fiche est « validée » au sens de KYC-04 : le dossier
# a franchi la validation, sa diligence est arrêtée. « vigilance_renforcee » et
# « bloque » n'en font pas partie — ce sont des états d'instruction, où la
# collecte documentaire par le clerc reste précisément ce qu'on attend de lui.
_STATUTS_FICHE_VALIDEE = ("valide", "traite", "cloture", "archive")


def _can_access(user: User, dossier: Dossier) -> bool:
    if user.is_supervisor:
        return True
    return dossier.assigned_to == user.id


async def _get_dossier_or_404(
    db: AsyncSession, dossier_id: str, user: User, *, ecriture: bool = False
) -> Dossier:
    """Résout un dossier accessible à l'appelant.

    `ecriture=True` ajoute le verrou d'archivage : CDC §5.2 place l'état
    « Archivé » en lecture seule, « aucune modification possible par aucun rôle »
    (Art. 23). La consultation d'un dossier archivé reste évidemment ouverte —
    c'est même l'objet de la conservation décennale.
    """
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not _can_access(user, dossier):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    if ecriture:
        archivage.assert_dossier_modifiable(dossier)
        # KYC-04 (CDC §7.3) — « Modifier une fiche validée » : O pour l'Admin, le
        # Notaire Principal et le Responsable Conformité, **N pour les Clercs**.
        # KYC-02 (« modifier une fiche EN COURS DE SAISIE ») leur reste ouvert :
        # la frontière est la validation du dossier. Sans ce contrôle, un clerc
        # pouvait réécrire l'état civil, la pièce d'identité ou le profil
        # financier d'une relation d'affaires déjà approuvée — et donc invalider
        # a posteriori la diligence sur laquelle le Notaire s'est engagé
        # (Art. 12, séparation des fonctions).
        if not user.is_supervisor and dossier.statut in _STATUTS_FICHE_VALIDEE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Modification d'une fiche validée réservée aux superviseurs (KYC-04).",
            )
    return dossier


# ── KYC PP ────────────────────────────────────────────────────────────────────

@router.get("/{dossier_id}/kyc/pp", response_model=KycPPOut)
async def get_kyc_pp(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPOut:
    # Appel conservé pour ses EFFETS : il valide l'existence du dossier (404) et
    # le droit d'accès de l'utilisateur (403). La valeur de retour n'est pas
    # utilisée ici — ne pas « nettoyer » cette ligne, ce serait ouvrir l'accès.
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC PP non trouvé.")
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pp_id == kyc.id))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pp_id == kyc.id))
    out = KycPPOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.put("/{dossier_id}/kyc/pp", response_model=KycPPOut)
async def upsert_kyc_pp(
    dossier_id: str,
    body: KycPPUpsert,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    data = body.model_dump()
    # Sérialise les sous-objets Pydantic en dict
    for field in ("mandataire", "operations_cochees", "origine_fonds"):
        if data.get(field) is not None and not isinstance(data[field], dict):
            data[field] = data[field].model_dump() if hasattr(data[field], "model_dump") else dict(data[field])
    kyc = await dossier_repo.upsert_kyc_pp(db, dossier_id, **data)
    # Recalcule le score provisoire (axes auto dérivés du KYC) — CDC Module 2
    result = await recompute_cache(db, dossier, current_user.id)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="kyc_pp.upserted",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={"classification": result.classification, "score": result.score},
    )
    # Criblage formel sanctions (T3 absolutoire si correspondance confirmée) — CDC §2.2
    await _check_sanctions_on_save(
        db, current_user=current_user, ip=ip, dossier=dossier,
        nom=f"{data.get('nom', '')} {data.get('prenoms', '')}".strip(),
        date_naissance=data.get("date_naissance"),
        lieu_naissance=data.get("lieu_naissance"),
        nationalite=data.get("nationalite"),
    )
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pp_id == kyc.id))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pp_id == kyc.id))
    out = KycPPOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


# ── Bénéficiaires effectifs PP ─────────────────────────────────────────────────

@router.post("/{dossier_id}/kyc/pp/be", response_model=KycBEOut, status_code=status.HTTP_201_CREATED)
async def add_be_pp(
    dossier_id: str,
    body: KycBECreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycBEOut:
    # Le dossier est nécessaire ici : il valide l'accès (404/403) ET sert au
    # criblage des listes de sanctions plus bas.
    dossier = await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PP d'abord.")
    be = KycBE(kyc_pp_id=kyc.id, **body.model_dump())
    db.add(be)
    await db.commit()
    await db.refresh(be)
    # Criblage formel du bénéficiaire effectif — CDC §2.2 (T3 si correspondance)
    ip = request.client.host if request.client else "unknown"
    await _check_sanctions_on_save(
        db, current_user=current_user, ip=ip, dossier=dossier,
        nom=body.raison_sociale_nom, date_naissance=body.date_naissance,
        lieu_naissance=body.lieu_naissance, nationalite=body.nationalite,
    )
    return KycBEOut.model_validate(be)


@router.delete("/{dossier_id}/kyc/pp/be/{be_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_be_pp(
    dossier_id: str,
    be_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    await db.execute(sa_delete(KycBE).where(KycBE.id == be_id))
    await db.commit()


async def _update_be(db: AsyncSession, be_id: str, body: KycBEUpdate) -> KycBE:
    result = await db.execute(select(KycBE).where(KycBE.id == be_id))
    be = result.scalar_one_or_none()
    if not be:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bénéficiaire effectif introuvable.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(be, k, v)
    await db.commit()
    await db.refresh(be)
    return be


@router.patch("/{dossier_id}/kyc/pp/be/{be_id}", response_model=KycBEOut)
async def update_be_pp(
    dossier_id: str,
    be_id: str,
    body: KycBEUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycBEOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    be = await _update_be(db, be_id, body)
    return KycBEOut.model_validate(be)


# ── PPE PP ────────────────────────────────────────────────────────────────────

@router.post("/{dossier_id}/kyc/pp/ppe", response_model=KycPPEOut, status_code=status.HTTP_201_CREATED)
async def add_ppe_pp(
    dossier_id: str,
    body: KycPPECreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPEOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    kyc = await dossier_repo.get_kyc_pp(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PP d'abord.")
    ppe = KycPPE(kyc_pp_id=kyc.id, **body.model_dump())
    db.add(ppe)
    await db.commit()
    await db.refresh(ppe)
    return KycPPEOut.model_validate(ppe)


@router.delete("/{dossier_id}/kyc/pp/ppe/{ppe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ppe_pp(
    dossier_id: str,
    ppe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    await db.execute(sa_delete(KycPPE).where(KycPPE.id == ppe_id))
    await db.commit()


async def _update_ppe(db: AsyncSession, ppe_id: str, body: KycPPEUpdate) -> KycPPE:
    result = await db.execute(select(KycPPE).where(KycPPE.id == ppe_id))
    ppe = result.scalar_one_or_none()
    if not ppe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Déclaration PPE introuvable.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ppe, k, v)
    await db.commit()
    await db.refresh(ppe)
    return ppe


@router.patch("/{dossier_id}/kyc/pp/ppe/{ppe_id}", response_model=KycPPEOut)
async def update_ppe_pp(
    dossier_id: str,
    ppe_id: str,
    body: KycPPEUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPEOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    return KycPPEOut.model_validate(await _update_ppe(db, ppe_id, body))


# ── KYC PM ────────────────────────────────────────────────────────────────────

@router.get("/{dossier_id}/kyc/pm", response_model=KycPMOut)
async def get_kyc_pm(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPMOut:
    await _get_dossier_or_404(db, dossier_id, current_user)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC PM non trouvé.")
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pm_id == kyc.id))
    act_result = await db.execute(select(KycActionnaire).where(KycActionnaire.kyc_pm_id == kyc.id).order_by(KycActionnaire.ordre))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pm_id == kyc.id))
    out = KycPMOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.actionnaires = [KycActOut.model_validate(a) for a in act_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.put("/{dossier_id}/kyc/pm", response_model=KycPMOut)
async def upsert_kyc_pm(
    dossier_id: str,
    body: KycPMUpsert,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPMOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    data = body.model_dump()
    for field in ("mandataire", "operations_cochees", "origine_fonds", "infos_pm"):
        if data.get(field) is not None and not isinstance(data[field], dict):
            data[field] = data[field].model_dump() if hasattr(data[field], "model_dump") else dict(data[field])
    # RCCM — validité 90 jours (M7) : expiration calculée + alerte proactive si dépassée
    from datetime import date as _date, timedelta as _timedelta
    emission = data.get("date_emission_rccm")
    if emission:
        data["date_expiration_rccm"] = emission + _timedelta(days=90)
        jours = (_date.today() - emission).days
        if jours > 90 and not await alertes_repo.exists_active(
            db, dossier_id=dossier_id, type_alerte="RCCM_EXPIRE"
        ):
            await alertes_repo.create(
                db, dossier_id=dossier_id, type_alerte="RCCM_EXPIRE",
                niveau="ELEVE" if jours > 120 else "MOYEN", statut="ouverte",
                description=f"Extrait RCCM émis il y a {jours} jours — validité 90 jours dépassée (M7).",
            )
    else:
        data["date_expiration_rccm"] = None
    kyc = await dossier_repo.upsert_kyc_pm(db, dossier_id, **data)
    # Recalcule le score provisoire (axes auto dérivés du KYC) — CDC Module 2
    result = await recompute_cache(db, dossier, current_user.id)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="kyc_pm.upserted",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dossier",
        entity_id=dossier_id,
        ip=ip,
        detail={"classification": result.classification, "score": result.score},
    )
    # Criblage formel sanctions — CDC §2.2. On crible séparément :
    #   1) la personne morale (dénomination sociale) — entité, sans date/lieu ;
    #   2) le représentant légal (personne physique) sur les 4 champs
    #      (nom+prénoms, date et lieu de naissance + nationalité), lus depuis le JSON
    #      `mandataire`. Criblage séparé = meilleur matching qu'une chaîne fusionnée.
    if data.get("denomination_sociale"):
        await _check_sanctions_on_save(
            db, current_user=current_user, ip=ip, dossier=dossier,
            nom=data["denomination_sociale"],
        )
    mand = data.get("mandataire") or {}
    rep_nom = (data.get("nom_representant_legal")
               or f"{mand.get('nom', '')} {mand.get('prenoms', '')}".strip())
    if rep_nom and len(rep_nom) >= 3:
        await _check_sanctions_on_save(
            db, current_user=current_user, ip=ip, dossier=dossier,
            nom=rep_nom,
            date_naissance=mand.get("date_naissance") or None,
            lieu_naissance=mand.get("lieu_naissance") or None,
            nationalite=mand.get("nationalite") or None,
        )
    be_result = await db.execute(select(KycBE).where(KycBE.kyc_pm_id == kyc.id))
    act_result = await db.execute(select(KycActionnaire).where(KycActionnaire.kyc_pm_id == kyc.id).order_by(KycActionnaire.ordre))
    ppe_result = await db.execute(select(KycPPE).where(KycPPE.kyc_pm_id == kyc.id))
    out = KycPMOut.model_validate(kyc)
    out.beneficiaires_effectifs = [KycBEOut.model_validate(b) for b in be_result.scalars().all()]
    out.actionnaires = [KycActOut.model_validate(a) for a in act_result.scalars().all()]
    out.ppe_declarations = [KycPPEOut.model_validate(p) for p in ppe_result.scalars().all()]
    return out


@router.post("/{dossier_id}/kyc/pm/be", response_model=KycBEOut, status_code=status.HTTP_201_CREATED)
async def add_be_pm(
    dossier_id: str,
    body: KycBECreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycBEOut:
    dossier = await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PM d'abord.")
    be = KycBE(kyc_pm_id=kyc.id, **body.model_dump())
    db.add(be)
    await db.commit()
    await db.refresh(be)
    # Criblage formel du bénéficiaire effectif — CDC §2.2 (T3 si correspondance)
    ip = request.client.host if request.client else "unknown"
    await _check_sanctions_on_save(
        db, current_user=current_user, ip=ip, dossier=dossier,
        nom=body.raison_sociale_nom, date_naissance=body.date_naissance,
        lieu_naissance=body.lieu_naissance, nationalite=body.nationalite,
    )
    return KycBEOut.model_validate(be)


@router.delete("/{dossier_id}/kyc/pm/be/{be_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_be_pm(
    dossier_id: str,
    be_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    await db.execute(sa_delete(KycBE).where(KycBE.id == be_id))
    await db.commit()


@router.patch("/{dossier_id}/kyc/pm/be/{be_id}", response_model=KycBEOut)
async def update_be_pm(
    dossier_id: str,
    be_id: str,
    body: KycBEUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycBEOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    be = await _update_be(db, be_id, body)
    return KycBEOut.model_validate(be)


@router.post("/{dossier_id}/kyc/pm/actionnaires", response_model=KycActOut, status_code=status.HTTP_201_CREATED)
async def add_actionnaire(
    dossier_id: str,
    body: KycActCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycActOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PM d'abord.")
    act = KycActionnaire(kyc_pm_id=kyc.id, **body.model_dump())
    db.add(act)
    await db.commit()
    await db.refresh(act)
    return KycActOut.model_validate(act)


@router.delete("/{dossier_id}/kyc/pm/actionnaires/{act_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_actionnaire(
    dossier_id: str,
    act_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    await db.execute(sa_delete(KycActionnaire).where(KycActionnaire.id == act_id))
    await db.commit()


@router.post("/{dossier_id}/kyc/pm/ppe", response_model=KycPPEOut, status_code=status.HTTP_201_CREATED)
async def add_ppe_pm(
    dossier_id: str,
    body: KycPPECreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPEOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    kyc = await dossier_repo.get_kyc_pm(db, dossier_id)
    if not kyc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Créer le KYC PM d'abord.")
    ppe = KycPPE(kyc_pm_id=kyc.id, **body.model_dump())
    db.add(ppe)
    await db.commit()
    await db.refresh(ppe)
    return KycPPEOut.model_validate(ppe)


@router.delete("/{dossier_id}/kyc/pm/ppe/{ppe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ppe_pm(
    dossier_id: str,
    ppe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    await db.execute(sa_delete(KycPPE).where(KycPPE.id == ppe_id))
    await db.commit()


@router.patch("/{dossier_id}/kyc/pm/ppe/{ppe_id}", response_model=KycPPEOut)
async def update_ppe_pm(
    dossier_id: str,
    ppe_id: str,
    body: KycPPEUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KycPPEOut:
    await _get_dossier_or_404(db, dossier_id, current_user, ecriture=True)
    return KycPPEOut.model_validate(await _update_ppe(db, ppe_id, body))
