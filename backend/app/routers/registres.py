"""Registres légaux — 6 registres basés sur audit_logs + export PDF (Art. 23, Ordonnance 2023-875)."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc
from app.models.audit import AuditLog
from app.models.user import User
from app.repositories import audit_repo

router = APIRouter(prefix="/registres", tags=["registres"])

REGISTRE_DEFS: dict[str, dict] = {
    "kyc": {
        "label": "Registre KYC",
        "filter_actions": ["dossier.created", "kyc.pp.saved", "kyc.pm.saved"],
        "confidential": False,
        "roles": None,
    },
    "alertes": {
        "label": "Registre des Alertes",
        "filter_actions": ["alerte.created", "alerte.traitee"],
        "confidential": False,
        "roles": None,
    },
    "dos": {
        "label": "Registre DOS (confidentiel — Art. 63)",
        "filter_actions": ["dos.created", "dos.soumis", "dos.accuse_recu", "dos.addendum"],
        "confidential": True,
        "roles": ["admin", "notaire_principal", "responsable_conformite"],
    },
    "statuts": {
        "label": "Registre des Changements de Statut",
        "filter_actions": ["dossier.statut_change"],
        "confidential": False,
        "roles": None,
    },
    "revisions": {
        "label": "Registre des Révisions KYC",
        "filter_actions": ["revision.created", "revision.validee"],
        "confidential": False,
        "roles": None,
    },
    "journal": {
        "label": "Journal des Actions Utilisateurs",
        "filter_actions": None,
        "confidential": False,
        "roles": ["admin", "responsable_conformite"],
    },
}


def _require_registre_access(reg_id: str, actor: User) -> None:
    reg = REGISTRE_DEFS.get(reg_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registre inconnu.")
    if reg.get("confidential") or reg.get("roles"):
        allowed = reg.get("roles") or ["admin", "notaire_principal", "responsable_conformite"]
        if actor.role not in allowed:
            raise HTTPException(status_code=403, detail="Accès non autorisé à ce registre.")


def _s(text: str) -> str:
    return (text or "").replace("—", "-").replace("–", "-").encode("latin-1", errors="replace").decode("latin-1")


def _generate_pdf(label: str, items: list[AuditLog]) -> bytes:
    from fpdf import FPDF
    from datetime import datetime, timezone

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_fill_color(26, 46, 74)
    pdf.set_text_color(232, 184, 75)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, _s(label), ln=True, fill=True, align="C")
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Exporte le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC", ln=True, align="C")
    pdf.set_text_color(220, 38, 38)
    pdf.cell(0, 5, "CONFIDENTIEL - Usage interne - Art. 23 (conservation 10 ans)", ln=True, align="C")
    pdf.ln(3)

    headers = ["Date/Heure", "Action", "Entite", "ID Entite", "Utilisateur", "IP"]
    col_w = [32, 45, 25, 35, 35, 18]
    pdf.set_fill_color(26, 46, 74)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 7, h, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for i, e in enumerate(items):
        pdf.set_fill_color(248, 250, 252) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 41, 59)
        ts = e.timestamp_utc.strftime("%d/%m/%Y %H:%M") if e.timestamp_utc else "-"
        row = [ts, (e.action or "")[:40], e.entity_type or "-", (e.entity_id or "-")[:30], (e.user_id or "-")[:30], e.ip or "-"]
        for w, v in zip(col_w, row):
            pdf.cell(w, 5, _s(str(v))[:38], fill=True)
        pdf.ln()

    return bytes(pdf.output())


@router.get("")
async def list_registres(current_user: User = Depends(get_current_user)) -> dict:
    visible = {}
    for key, reg in REGISTRE_DEFS.items():
        if reg.get("confidential") or reg.get("roles"):
            allowed = reg.get("roles") or ["admin", "notaire_principal", "responsable_conformite"]
            if current_user.role not in allowed:
                continue
        visible[key] = {"id": key, "label": reg["label"], "confidential": reg.get("confidential", False)}
    return {"registres": list(visible.values())}


@router.get("/{registre_id}")
async def get_registre(
    registre_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _require_registre_access(registre_id, current_user)
    reg = REGISTRE_DEFS[registre_id]

    q = select(AuditLog).order_by(AuditLog.timestamp_utc.desc())
    if reg.get("filter_actions"):
        q = q.where(AuditLog.action.in_(reg["filter_actions"]))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await db.execute(q.limit(limit).offset(offset))
    items = result.scalars().all()

    return {
        "id": registre_id,
        "label": reg["label"],
        "total": total,
        "items": [
            {
                "id": e.id,
                "timestamp": e.timestamp_utc.isoformat() if e.timestamp_utc else None,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "user_id": e.user_id,
                "user_role": e.user_role,
                "ip": e.ip,
                "detail": e.detail,
            }
            for e in items
        ],
    }


@router.get("/{registre_id}/export")
async def export_registre(
    registre_id: str,
    format: str = Query("pdf", regex="^(pdf)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _require_registre_access(registre_id, current_user)
    reg = REGISTRE_DEFS[registre_id]

    q = select(AuditLog).order_by(AuditLog.timestamp_utc.desc()).limit(1000)
    if reg.get("filter_actions"):
        q = q.where(AuditLog.action.in_(reg["filter_actions"]))
    result = await db.execute(q)
    items = list(result.scalars().all())

    from datetime import datetime, timezone
    await audit_repo.log(
        db,
        action=f"registre.{registre_id}.exported",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="registre",
        entity_id=registre_id,
        ip="internal",
        detail={"format": format, "count": len(items)},
    )

    pdf_bytes = _generate_pdf(reg["label"], items)
    filename = f"registre-{registre_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/dashboard/stats")
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dashboard stats — rôle filtré."""
    from app.models.dossier import Dossier
    from app.models.alerte import Alerte
    from app.models.revision import RevisionKyc
    from datetime import date

    total_dossiers = (await db.execute(select(func.count()).select_from(Dossier))).scalar_one()
    by_classification = (await db.execute(
        select(Dossier.classification, func.count()).group_by(Dossier.classification)
    )).all()
    alertes_ouvertes = (await db.execute(
        select(func.count()).select_from(Alerte).where(Alerte.statut == "ouverte")
    )).scalar_one()
    revisions_en_retard = (await db.execute(
        select(func.count()).select_from(RevisionKyc).where(
            RevisionKyc.statut == "planifiee",
            RevisionKyc.date_echeance < date.today(),
        )
    )).scalar_one()

    stats: dict = {
        "total_dossiers": total_dossiers,
        "alertes_ouvertes": alertes_ouvertes,
        "revisions_en_retard": revisions_en_retard,
        "by_classification": [{"classification": c or "NON_EVALUE", "count": n} for c, n in by_classification],
    }

    if current_user.role in ("admin", "notaire_principal", "responsable_conformite"):
        from app.models.dos import DeclarationSuspicion
        dos_total = (await db.execute(select(func.count()).select_from(DeclarationSuspicion))).scalar_one()
        dos_en_cours = (await db.execute(
            select(func.count()).select_from(DeclarationSuspicion).where(
                DeclarationSuspicion.statut.in_(["brouillon", "en_cours"])
            )
        )).scalar_one()
        stats["dos_total"] = dos_total
        stats["dos_en_cours"] = dos_en_cours

    return stats
