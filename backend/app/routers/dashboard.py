"""Tableau de bord — statistiques agrégées, filtrées par rôle.

Le frontend (DashboardView.vue) consomme cet endpoint à `/api/dashboard/stats`.
Superviseurs (admin / notaire_principal / responsable_conformite) : vue globale.
Autres rôles (clercs) : périmètre limité aux dossiers qui leur sont assignés.
"""
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.dossier import Dossier
from app.models.alerte import Alerte
from app.models.revision import RevisionKyc
from app.models.dos import DeclarationSuspicion

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Statuts hors flux actif. « resilie » figurait ici alors qu'il n'appartient pas
# à `statut_dossier_enum` (héritage du vertical immobilier, où un contrat peut
# être résilié) : MySQL tolérait la comparaison à une valeur hors énumération,
# PostgreSQL la rejette — d'où une 500 sur tout le tableau de bord. Les statuts
# valides sont : brouillon, en_analyse, vigilance_renforcee, valide, bloque,
# traite, cloture, archive.
_STATUTS_INACTIFS = ("cloture", "archive")


def _recent_payload(rows) -> list[dict]:
    return [
        {
            "id": r.id,
            "reference": r.reference,
            "type_client": r.type_client,
            "statut": r.statut,
            "niveau_risque": r.classification,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/stats")
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)

    if not current_user.is_supervisor:
        # ── Vue opérationnelle (clercs) : dossiers assignés ───────────────────
        scope = Dossier.assigned_to == current_user.id
        mes_dossiers_q = (
            select(Dossier.statut, func.count())
            .where(and_(scope, Dossier.statut.not_in(_STATUTS_INACTIFS)))
            .group_by(Dossier.statut)
        )
        mes_dossiers = dict((await db.execute(mes_dossiers_q)).all())

        alertes_ouvertes = (await db.execute(
            select(func.count()).select_from(Alerte)
            .join(Dossier, Alerte.dossier_id == Dossier.id)
            .where(Alerte.statut == "ouverte", scope)
        )).scalar_one()

        recent = (await db.execute(
            select(
                Dossier.id, Dossier.reference, Dossier.type_client,
                Dossier.statut, Dossier.classification, Dossier.created_at,
            ).where(scope).order_by(Dossier.created_at.desc()).limit(8)
        )).all()

        # Métriques KPI (alignées sur immo) : KYC en analyse, DOS ouvertes,
        # dossiers risque élevé, total dossiers depuis le 1ᵉʳ janvier.
        annee_debut = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        dossiers_annee = (await db.execute(
            select(func.count()).select_from(Dossier).where(
                and_(scope, Dossier.created_at >= annee_debut)
            )
        )).scalar_one()
        risque_eleve = (await db.execute(
            select(func.count()).select_from(Dossier).where(
                and_(scope, Dossier.classification == "ELEVE")
            )
        )).scalar_one()
        # DOS — cloisonnement (CDC §7.3 DOS-04 « Consulter les DOS existants : Clercs N »,
        # §6.2 et §8.5 Art. 63). Cette métrique comptait auparavant TOUTES les DOS du
        # cabinet, sans aucun filtre de périmètre : un clerc lisait donc, depuis son
        # tableau de bord, le volume d'activité déclarative du cabinet — à la fois une
        # statistique globale interdite par P³ et une information DOS interdite par
        # DOS-04. Le compteur est neutralisé pour les rôles opérationnels : la
        # confidentialité du DOS prime sur la complétude du tableau de bord.
        dos_ouvertes = 0

        return {
            "role": current_user.role,
            "scope": "assigne",
            "mes_dossiers_by_statut": mes_dossiers,
            "kyc_en_analyse": mes_dossiers.get("en_analyse", 0),
            "dos_ouvertes": dos_ouvertes,
            "dossiers_risque_eleve": risque_eleve,
            "dossiers_annee": dossiers_annee,
            "alertes_ouvertes": alertes_ouvertes,
            "recent_dossiers": _recent_payload(recent),
        }

    # ── Vue superviseur : globale ─────────────────────────────────────────────
    dossiers_by_statut = dict((await db.execute(
        select(Dossier.statut, func.count())
        .where(Dossier.statut.not_in(_STATUTS_INACTIFS))
        .group_by(Dossier.statut)
    )).all())

    risque_distribution = dict((await db.execute(
        select(Dossier.classification, func.count())
        .where(Dossier.classification.isnot(None))
        .group_by(Dossier.classification)
    )).all())

    alertes_ouvertes = (await db.execute(
        select(func.count()).select_from(Alerte).where(Alerte.statut == "ouverte")
    )).scalar_one()

    revisions_dues_30j = (await db.execute(
        select(func.count()).select_from(RevisionKyc).where(
            and_(
                RevisionKyc.statut.in_(["planifiee", "en_retard"]),
                RevisionKyc.date_echeance <= date.today() + timedelta(days=30),
            )
        )
    )).scalar_one()

    # WRK09 : dossiers PPE (T1) en attente de décision Notaire Principal
    wrk09_en_attente = (await db.execute(
        select(func.count()).select_from(Dossier).where(
            and_(Dossier.trigger_actif == "T1", Dossier.statut == "en_analyse")
        )
    )).scalar_one()

    # Métriques KPI (alignées sur immo) : DOS ouvertes + total dossiers depuis le 1ᵉʳ janvier.
    annee_debut = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    dossiers_annee = (await db.execute(
        select(func.count()).select_from(Dossier).where(Dossier.created_at >= annee_debut)
    )).scalar_one()
    dos_ouvertes = (await db.execute(
        select(func.count()).select_from(DeclarationSuspicion).where(
            DeclarationSuspicion.statut == "brouillon"
        )
    )).scalar_one()

    recent = (await db.execute(
        select(
            Dossier.id, Dossier.reference, Dossier.type_client,
            Dossier.statut, Dossier.classification, Dossier.created_at,
        ).order_by(Dossier.created_at.desc()).limit(8)
    )).all()

    # ── Données mensuelles (6 derniers mois calendaires) ──────────────────────
    months_6: list[str] = []
    y, m = now.year, now.month
    for _ in range(6):
        months_6.insert(0, f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1

    cutoff = datetime(y, m + 1, 1, tzinfo=timezone.utc) if m < 12 else datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    monthly_rows = (await db.execute(
        select(Dossier.created_at, Dossier.statut, Dossier.classification)
        .where(Dossier.created_at >= cutoff)
    )).all()

    counts: dict = defaultdict(int)
    valide: dict = defaultdict(int)
    risque: dict = defaultdict(int)
    for r in monthly_rows:
        if not r.created_at:
            continue
        key = r.created_at.strftime("%Y-%m")
        counts[key] += 1
        if r.statut in ("valide", "actif", "actif_sous_surveillance", "traite"):
            valide[key] += 1
        if r.classification == "ELEVE":
            risque[key] += 1

    monthly_data = []
    for key in months_6:
        yr, mo = int(key[:4]), int(key[5:])
        monthly_data.append({
            "mois": datetime(yr, mo, 1).strftime("%b"),
            "soumissions": counts.get(key, 0),
            "valides": valide.get(key, 0),
            "risques": risque.get(key, 0),
        })

    return {
        "role": current_user.role,
        "scope": "global",
        "dossiers_by_statut": dossiers_by_statut,
        "risque_distribution": risque_distribution,
        "kyc_en_analyse": dossiers_by_statut.get("en_analyse", 0),
        "dos_ouvertes": dos_ouvertes,
        "dossiers_risque_eleve": risque_distribution.get("ELEVE", 0),
        "dossiers_annee": dossiers_annee,
        "alertes_ouvertes": alertes_ouvertes,
        "revisions_dues_30j": revisions_dues_30j,
        "wrk09_en_attente": wrk09_en_attente,
        "recent_dossiers": _recent_payload(recent),
        "monthly_data": monthly_data,
    }
