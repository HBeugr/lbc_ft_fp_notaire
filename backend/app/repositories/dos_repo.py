from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dos import DeclarationSuspicion, DosAddendum


async def get_by_id(db: AsyncSession, dos_id: str) -> DeclarationSuspicion | None:
    result = await db.execute(select(DeclarationSuspicion).where(DeclarationSuspicion.id == dos_id))
    return result.scalar_one_or_none()


async def get_by_dossier(db: AsyncSession, dossier_id: str) -> DeclarationSuspicion | None:
    result = await db.execute(
        select(DeclarationSuspicion).where(DeclarationSuspicion.dossier_id == dossier_id)
    )
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[DeclarationSuspicion]:
    result = await db.execute(
        select(DeclarationSuspicion).order_by(DeclarationSuspicion.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def create(db: AsyncSession, **kwargs) -> DeclarationSuspicion:
    dos = DeclarationSuspicion(**kwargs)
    db.add(dos)
    await db.commit()
    await db.refresh(dos)
    return dos


async def update(db: AsyncSession, dos: DeclarationSuspicion, **kwargs) -> DeclarationSuspicion:
    for k, v in kwargs.items():
        setattr(dos, k, v)
    await db.commit()
    await db.refresh(dos)
    return dos


async def add_addendum(db: AsyncSession, dos_id: str, user_id: str, contenu: str) -> DosAddendum:
    addendum = DosAddendum(dos_id=dos_id, user_id=user_id, contenu=contenu)
    db.add(addendum)
    await db.commit()
    await db.refresh(addendum)
    return addendum
