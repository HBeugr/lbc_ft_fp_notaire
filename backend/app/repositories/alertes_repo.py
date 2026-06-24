from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.alerte import Alerte, AutorisationDirigeant

# Types d'alertes « notification » (vs « conformité »). Notaire n'en génère pas
# actuellement — tuple vide → catégorie 'conformite' = toutes les alertes.
NOTIFICATION_TYPES: tuple[str, ...] = ()


def _filtered_alertes_query(base, *, statut=None, niveau=None, type_alerte=None, dossier_id=None,
                            categorie=None, dossier_statut=None, assigned_to=None):
    if statut:
        base = base.where(Alerte.statut == statut)
    if niveau:
        base = base.where(Alerte.niveau == niveau)
    if type_alerte:
        base = base.where(Alerte.type_alerte == type_alerte)
    if dossier_id:
        base = base.where(Alerte.dossier_id == dossier_id)
    if categorie == "notification" and NOTIFICATION_TYPES:
        base = base.where(Alerte.type_alerte.in_(NOTIFICATION_TYPES))
    elif categorie == "conformite" and NOTIFICATION_TYPES:
        base = base.where(Alerte.type_alerte.not_in(NOTIFICATION_TYPES))
    # Jointure Dossier unique (cloisonnement par assigné et/ou filtre statut dossier)
    if dossier_statut or assigned_to:
        from app.models.dossier import Dossier
        base = base.join(Dossier, Dossier.id == Alerte.dossier_id)
        if dossier_statut:
            base = base.where(Dossier.statut == dossier_statut)
        if assigned_to:
            base = base.where(Dossier.assigned_to == assigned_to)
    return base


async def list_alertes(
    db: AsyncSession,
    statut: str | None = None,
    niveau: str | None = None,
    type_alerte: str | None = None,
    dossier_id: str | None = None,
    categorie: str | None = None,
    dossier_statut: str | None = None,
    assigned_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Alerte], int]:
    filters = dict(statut=statut, niveau=niveau, type_alerte=type_alerte, dossier_id=dossier_id,
                   categorie=categorie, dossier_statut=dossier_statut, assigned_to=assigned_to)
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


async def count_non_traitees_critiques(db: AsyncSession, dossier_id: str | None) -> int:
    """Nb d'alertes ÉLEVÉ non traitées (ouverte/en_cours) sur le dossier.
    Garde-fou de validation : on ne valide pas un dossier avec une alerte critique ouverte."""
    if not dossier_id:
        return 0
    q = select(func.count(Alerte.id)).where(
        Alerte.dossier_id == dossier_id,
        Alerte.niveau == "ELEVE",
        Alerte.statut.in_(("ouverte", "en_cours")),
    )
    return (await db.execute(q)).scalar_one()


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


_STATUTS_ACTIFS = ("ouverte", "en_cours")


async def exists_active(db: AsyncSession, *, dossier_id: str | None, type_alerte: str) -> bool:
    """True si une alerte active (ouverte/en_cours) du même type existe déjà sur le dossier.

    Anti-doublon : le criblage sanctions et certains contrôles (RCCM…) sont rejoués à
    chaque sauvegarde du dossier ; sans ce garde-fou, chaque ré-enregistrement empile
    une alerte identique."""
    if not dossier_id:
        return False
    result = await db.execute(
        select(func.count(Alerte.id)).where(
            Alerte.dossier_id == dossier_id,
            Alerte.type_alerte == type_alerte,
            Alerte.statut.in_(_STATUTS_ACTIFS),
        )
    )
    return (result.scalar_one() or 0) > 0


async def resoudre_actives_par_type(
    db: AsyncSession,
    *,
    dossier_id: str | None,
    type_alerte: str,
    traite_par: str | None = None,
    note: str | None = None,
) -> int:
    """Passe en 'traitee' les alertes actives du même type sur le dossier (consolidation
    au traitement — referme les doublons en conservant une trace traitée). Ne committe
    pas : l'appelant gère la transaction. Retourne le nombre d'alertes consolidées."""
    from datetime import datetime, timezone
    if not dossier_id:
        return 0
    result = await db.execute(
        select(Alerte).where(
            Alerte.dossier_id == dossier_id,
            Alerte.type_alerte == type_alerte,
            Alerte.statut.in_(_STATUTS_ACTIFS),
        )
    )
    n = 0
    for a in result.scalars().all():
        a.statut = "traitee"
        a.traite_par = traite_par
        a.traite_at = datetime.now(timezone.utc)
        a.resolution_note = a.resolution_note or note or "Doublon consolidé automatiquement."
        n += 1
    return n


# ── WRK-09 (autorisations Notaire Principal sur dossiers T1/PPE) ────────────────

async def get_pending_wrk09(db: AsyncSession):
    """Dossiers avec Trigger T1 actif, non clôturés/bloqués, sans décision WRK-09 enregistrée.

    Retourne des objets Dossier (l'appelant sérialise)."""
    from app.models.dossier import Dossier
    sub = select(AutorisationDirigeant.dossier_id)
    q = (
        select(Dossier)
        .where(
            Dossier.trigger_actif == "T1",
            Dossier.statut.notin_(("cloture", "archive", "bloque")),
            Dossier.id.notin_(sub),
        )
        .order_by(Dossier.created_at.desc())
    )
    return list((await db.execute(q)).scalars().all())


async def has_autorisation(db: AsyncSession, dossier_id: str) -> bool:
    r = await db.execute(
        select(func.count(AutorisationDirigeant.id)).where(AutorisationDirigeant.dossier_id == dossier_id)
    )
    return (r.scalar_one() or 0) > 0


async def create_autorisation(
    db: AsyncSession, *, dossier_id: str, dirigeant_id: str, decision: str, justification: str | None
) -> AutorisationDirigeant:
    autorisation = AutorisationDirigeant(
        dossier_id=dossier_id, dirigeant_id=dirigeant_id,
        decision=decision, justification=justification,
    )
    db.add(autorisation)
    await db.commit()
    await db.refresh(autorisation)
    return autorisation
