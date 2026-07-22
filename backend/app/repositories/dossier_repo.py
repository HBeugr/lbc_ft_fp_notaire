from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.models.dossier import Dossier, KycPP, KycPM, DossierHistorique, CommentaireInterne


def _with_kyc(q):
    """Charge les relations KYC PP/PM et leurs sous-collections pour éviter les
    lazy-loads asynchrones lors de la sérialisation DossierOut."""
    return q.options(
        selectinload(Dossier.kyc_pp).selectinload(KycPP.beneficiaires_effectifs),
        selectinload(Dossier.kyc_pp).selectinload(KycPP.ppe_declarations),
        selectinload(Dossier.kyc_pm).selectinload(KycPM.beneficiaires_effectifs),
        selectinload(Dossier.kyc_pm).selectinload(KycPM.actionnaires),
        selectinload(Dossier.kyc_pm).selectinload(KycPM.ppe_declarations),
    )


def _apply_dossier_filters(q, *, assigned_to=None, statut=None, classification=None, reference=None, search=None):
    if assigned_to:
        q = q.where(Dossier.assigned_to == assigned_to)
    if statut:
        q = q.where(Dossier.statut == statut)
    if classification:
        q = q.where(Dossier.classification == classification)
    if reference:
        q = q.where(Dossier.reference.ilike(f"%{reference}%"))
    # Recherche libre : référence (KYC-…) OU nom du client
    # (PP : nom/prénoms, PM : dénomination sociale). KycPP/KycPM sont en 1-à-1
    # avec Dossier, donc l'outerjoin n'introduit pas de doublons.
    if search:
        like = f"%{search.strip()}%"
        q = (
            q.outerjoin(KycPP, KycPP.dossier_id == Dossier.id)
            .outerjoin(KycPM, KycPM.dossier_id == Dossier.id)
            .where(or_(
                Dossier.reference.ilike(like),
                KycPP.nom.ilike(like),
                KycPP.prenoms.ilike(like),
                KycPM.denomination_sociale.ilike(like),
            ))
        )
    return q


async def get_by_id(db: AsyncSession, dossier_id: str) -> Dossier | None:
    result = await db.execute(_with_kyc(select(Dossier)).where(Dossier.id == dossier_id))
    return result.scalar_one_or_none()


async def get_by_reference(db: AsyncSession, reference: str) -> Dossier | None:
    result = await db.execute(
        _with_kyc(select(Dossier)).where(Dossier.reference == reference)
    )
    return result.scalar_one_or_none()


async def list_dossiers(
    db: AsyncSession,
    assigned_to: str | None = None,
    statut: str | None = None,
    classification: str | None = None,
    reference: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Dossier]:
    q = _apply_dossier_filters(
        _with_kyc(select(Dossier)),
        assigned_to=assigned_to, statut=statut,
        classification=classification, reference=reference, search=search,
    )
    q = q.order_by(Dossier.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def count_dossiers(
    db: AsyncSession,
    assigned_to: str | None = None,
    statut: str | None = None,
    classification: str | None = None,
    reference: str | None = None,
    search: str | None = None,
) -> int:
    q = _apply_dossier_filters(
        select(func.count(Dossier.id)),
        assigned_to=assigned_to, statut=statut,
        classification=classification, reference=reference, search=search,
    )
    result = await db.execute(q)
    return result.scalar_one()


async def create(db: AsyncSession, **kwargs) -> Dossier:
    dossier = Dossier(**kwargs)
    db.add(dossier)
    await db.commit()
    await db.refresh(dossier)
    return dossier


async def update_statut(
    db: AsyncSession,
    dossier: Dossier,
    new_statut: str,
    user_id: str,
    commentaire: str | None = None,
) -> Dossier:
    old_statut = dossier.statut
    dossier.statut = new_statut
    historique = DossierHistorique(
        dossier_id=dossier.id,
        statut_avant=old_statut,
        statut_apres=new_statut,
        user_id=user_id,
        commentaire=commentaire,
    )
    db.add(historique)
    await db.commit()
    await db.refresh(dossier)
    return dossier


async def add_commentaire(
    db: AsyncSession,
    dossier_id: str,
    user_id: str,
    contenu: str,
) -> CommentaireInterne:
    commentaire = CommentaireInterne(
        dossier_id=dossier_id, user_id=user_id, contenu=contenu
    )
    db.add(commentaire)
    await db.commit()
    await db.refresh(commentaire)
    return commentaire


async def get_kyc_pp(db: AsyncSession, dossier_id: str) -> KycPP | None:
    # eager-load des relations : évite un lazy-load async (MissingGreenlet) lors de
    # la sérialisation KycPPOut.model_validate(kyc).
    result = await db.execute(
        select(KycPP)
        .options(selectinload(KycPP.beneficiaires_effectifs), selectinload(KycPP.ppe_declarations))
        .where(KycPP.dossier_id == dossier_id)
    )
    return result.scalar_one_or_none()


async def get_kyc_pm(db: AsyncSession, dossier_id: str) -> KycPM | None:
    result = await db.execute(
        select(KycPM)
        .options(
            selectinload(KycPM.beneficiaires_effectifs),
            selectinload(KycPM.ppe_declarations),
            selectinload(KycPM.actionnaires),
        )
        .where(KycPM.dossier_id == dossier_id)
    )
    return result.scalar_one_or_none()


async def upsert_kyc_pp(db: AsyncSession, dossier_id: str, **kwargs) -> KycPP:
    existing = await get_kyc_pp(db, dossier_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        await db.commit()
    else:
        db.add(KycPP(dossier_id=dossier_id, **kwargs))
        await db.commit()
    # Re-fetch avec relations eager-loadées (sérialisation sûre en async)
    return await get_kyc_pp(db, dossier_id)


async def upsert_kyc_pm(db: AsyncSession, dossier_id: str, **kwargs) -> KycPM:
    existing = await get_kyc_pm(db, dossier_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        await db.commit()
    else:
        db.add(KycPM(dossier_id=dossier_id, **kwargs))
        await db.commit()
    return await get_kyc_pm(db, dossier_id)
