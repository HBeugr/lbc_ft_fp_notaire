from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sanction import ListeSanctions, EntreeSanction


def _cap(value, limit: int) -> str | None:
    """Tronque une valeur à la longueur max de la colonne (évite 'Data too long').

    Le parser peut sur-capturer certains champs (ex. nationalité ONU mêlée à du
    texte arabe / des dates) ; on borne défensivement avant insertion.
    """
    if not value:
        return None
    return str(value)[:limit]


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
            nom=_cap(e.get("nom"), 500) or "",
            date_naissance=_cap(e.get("date_naissance"), 40),
            nationalite=_cap(e.get("nationalite"), 120),
            lieu_naissance=_cap(e.get("lieu_naissance"), 255),
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
