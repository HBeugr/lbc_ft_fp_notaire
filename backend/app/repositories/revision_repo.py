from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.revision import RevisionKyc


async def get_by_id(db: AsyncSession, revision_id: str) -> RevisionKyc | None:
    result = await db.execute(select(RevisionKyc).where(RevisionKyc.id == revision_id))
    return result.scalar_one_or_none()


async def get_by_dossier(db: AsyncSession, dossier_id: str) -> list[RevisionKyc]:
    result = await db.execute(
        select(RevisionKyc).where(RevisionKyc.dossier_id == dossier_id).order_by(RevisionKyc.date_echeance)
    )
    return list(result.scalars().all())


async def list_a_venir(db: AsyncSession, jours: int = 30) -> list[RevisionKyc]:
    from datetime import timedelta
    limite = date.today() + timedelta(days=jours)
    result = await db.execute(
        select(RevisionKyc)
        .where(RevisionKyc.statut == "planifiee", RevisionKyc.date_echeance <= limite)
        .order_by(RevisionKyc.date_echeance)
    )
    return list(result.scalars().all())


async def list_en_retard(db: AsyncSession) -> list[RevisionKyc]:
    result = await db.execute(
        select(RevisionKyc)
        .where(RevisionKyc.statut == "planifiee", RevisionKyc.date_echeance < date.today())
        .order_by(RevisionKyc.date_echeance)
    )
    return list(result.scalars().all())


async def create(db: AsyncSession, **kwargs) -> RevisionKyc:
    revision = RevisionKyc(**kwargs)
    db.add(revision)
    await db.commit()
    await db.refresh(revision)
    return revision


async def update(db: AsyncSession, revision: RevisionKyc, **kwargs) -> RevisionKyc:
    for k, v in kwargs.items():
        setattr(revision, k, v)
    await db.commit()
    await db.refresh(revision)
    return revision
