from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.dossier import Dossier, KycPP, KycPM, DossierHistorique, CommentaireInterne


async def get_by_id(db: AsyncSession, dossier_id: str) -> Dossier | None:
    result = await db.execute(select(Dossier).where(Dossier.id == dossier_id))
    return result.scalar_one_or_none()


async def get_by_reference(db: AsyncSession, reference: str) -> Dossier | None:
    result = await db.execute(select(Dossier).where(Dossier.reference == reference))
    return result.scalar_one_or_none()


async def list_dossiers(
    db: AsyncSession,
    assigned_to: str | None = None,
    statut: str | None = None,
    classification: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Dossier]:
    q = select(Dossier)
    if assigned_to:
        q = q.where(Dossier.assigned_to == assigned_to)
    if statut:
        q = q.where(Dossier.statut == statut)
    if classification:
        q = q.where(Dossier.classification == classification)
    q = q.order_by(Dossier.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def count_dossiers(db: AsyncSession, **filters) -> int:
    q = select(func.count(Dossier.id))
    if filters.get("statut"):
        q = q.where(Dossier.statut == filters["statut"])
    if filters.get("classification"):
        q = q.where(Dossier.classification == filters["classification"])
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
    result = await db.execute(select(KycPP).where(KycPP.dossier_id == dossier_id))
    return result.scalar_one_or_none()


async def get_kyc_pm(db: AsyncSession, dossier_id: str) -> KycPM | None:
    result = await db.execute(select(KycPM).where(KycPM.dossier_id == dossier_id))
    return result.scalar_one_or_none()


async def upsert_kyc_pp(db: AsyncSession, dossier_id: str, **kwargs) -> KycPP:
    existing = await get_kyc_pp(db, dossier_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return existing
    kyc = KycPP(dossier_id=dossier_id, **kwargs)
    db.add(kyc)
    await db.commit()
    await db.refresh(kyc)
    return kyc


async def upsert_kyc_pm(db: AsyncSession, dossier_id: str, **kwargs) -> KycPM:
    existing = await get_kyc_pm(db, dossier_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return existing
    kyc = KycPM(dossier_id=dossier_id, **kwargs)
    db.add(kyc)
    await db.commit()
    await db.refresh(kyc)
    return kyc
