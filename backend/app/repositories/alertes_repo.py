from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.alerte import Alerte


def _filtered_alertes_query(base, *, statut=None, niveau=None, type_alerte=None, dossier_id=None):
    if statut:
        base = base.where(Alerte.statut == statut)
    if niveau:
        base = base.where(Alerte.niveau == niveau)
    if type_alerte:
        base = base.where(Alerte.type_alerte == type_alerte)
    if dossier_id:
        base = base.where(Alerte.dossier_id == dossier_id)
    return base


async def list_alertes(
    db: AsyncSession,
    statut: str | None = None,
    niveau: str | None = None,
    type_alerte: str | None = None,
    dossier_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Alerte], int]:
    filters = dict(statut=statut, niveau=niveau, type_alerte=type_alerte, dossier_id=dossier_id)
    total = (await db.execute(
        _filtered_alertes_query(select(func.count(Alerte.id)), **filters)
    )).scalar_one()
    q = _filtered_alertes_query(select(Alerte), **filters).order_by(Alerte.created_at.desc())
    items = list((await db.execute(q.limit(limit).offset(offset))).scalars().all())
    return items, total


async def list_by_signaleur(db: AsyncSession, signaleur_id: str) -> list[Alerte]:
    result = await db.execute(
        select(Alerte).where(Alerte.signaleur_id == signaleur_id).order_by(Alerte.created_at.desc())
    )
    return list(result.scalars().all())


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


async def count_open_for_user(db: AsyncSession, user_id: str, is_supervisor: bool) -> int:
    """Compteur d'alertes non traitées pour le badge temps réel.

    - Superviseur (admin/notaire principal/RC) : toutes les alertes ouvertes/en cours.
    - Autres (clercs…) : alertes sur les dossiers qui leur sont assignés.
    """
    from app.models.dossier import Dossier
    q = select(func.count(Alerte.id)).where(Alerte.statut.in_(("ouverte", "en_cours")))
    if not is_supervisor:
        q = q.join(Dossier, Dossier.id == Alerte.dossier_id).where(Dossier.assigned_to == user_id)
    return (await db.execute(q)).scalar_one()


async def update_statut(db: AsyncSession, alerte: Alerte, statut: str, traite_par: str, note: str | None = None) -> Alerte:
    from datetime import datetime, timezone
    alerte.statut = statut
    alerte.traite_par = traite_par
    alerte.traite_at = datetime.now(timezone.utc)
    alerte.resolution_note = note
    await db.commit()
    await db.refresh(alerte)
    return alerte
