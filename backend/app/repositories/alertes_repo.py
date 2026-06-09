from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.alerte import Alerte


async def create(db: AsyncSession, **kwargs) -> Alerte:
    alerte = Alerte(**kwargs)
    db.add(alerte)
    await db.commit()
    await db.refresh(alerte)
    return alerte


async def get_by_dossier(db: AsyncSession, dossier_id: str) -> list[Alerte]:
    result = await db.execute(
        select(Alerte).where(Alerte.dossier_id == dossier_id).order_by(Alerte.created_at.desc())
    )
    return list(result.scalars().all())


async def list_ouvertes(db: AsyncSession, limit: int = 100) -> list[Alerte]:
    result = await db.execute(
        select(Alerte).where(Alerte.statut == "ouverte").order_by(Alerte.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def update_statut(db: AsyncSession, alerte: Alerte, statut: str, traite_par: str, note: str | None = None) -> Alerte:
    from datetime import datetime, timezone
    alerte.statut = statut
    alerte.traite_par = traite_par
    alerte.traite_at = datetime.now(timezone.utc)
    alerte.resolution_note = note
    await db.commit()
    await db.refresh(alerte)
    return alerte
