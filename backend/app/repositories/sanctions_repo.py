from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sanction import ListeSanctions, EntreeSanction


async def create_liste(
    db: AsyncSession,
    *,
    nom: str,
    type_liste: str,
    uploaded_by: str | None,
    entries: list[dict],
) -> ListeSanctions:
    """Crée une liste + ses entrées normalisées. total_entrees = nb d'entrées."""
    liste = ListeSanctions(
        nom=nom,
        type_liste=type_liste,
        uploaded_by=uploaded_by,
        total_entrees=len(entries),
        is_active=True,
    )
    db.add(liste)
    await db.flush()  # obtient liste.id
    for e in entries:
        db.add(EntreeSanction(
            liste_id=liste.id,
            nom=e["nom"],
            date_naissance=(e.get("date_naissance") or None),
            nationalite=(e.get("nationalite") or None),
            lieu_naissance=(e.get("lieu_naissance") or None),
        ))
    await db.commit()
    await db.refresh(liste)
    return liste


async def list_active(db: AsyncSession) -> list[ListeSanctions]:
    res = await db.execute(
        select(ListeSanctions)
        .where(ListeSanctions.is_active.is_(True))
        .order_by(ListeSanctions.activated_at.desc())
    )
    return list(res.scalars().all())


async def get_active_with_entries(db: AsyncSession) -> list[ListeSanctions]:
    """Listes actives, chaque liste recevant un attribut transient `.entrees`."""
    listes = await list_active(db)
    if not listes:
        return []
    ids = [liste.id for liste in listes]
    res = await db.execute(select(EntreeSanction).where(EntreeSanction.liste_id.in_(ids)))
    by_liste: dict[str, list[EntreeSanction]] = {}
    for entree in res.scalars().all():
        by_liste.setdefault(entree.liste_id, []).append(entree)
    for liste in listes:
        liste.entrees = by_liste.get(liste.id, [])
    return listes


async def get_by_id(db: AsyncSession, liste_id: str) -> ListeSanctions | None:
    res = await db.execute(select(ListeSanctions).where(ListeSanctions.id == liste_id))
    return res.scalar_one_or_none()


async def deactivate(db: AsyncSession, liste: ListeSanctions) -> None:
    liste.is_active = False
    await db.commit()
