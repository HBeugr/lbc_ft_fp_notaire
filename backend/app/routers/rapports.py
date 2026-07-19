"""Rapports PDF — conformité, client, audit (Art. 23, Ordonnance 2023-875)."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_rc
from app.models.user import User
from app.models.dossier import Dossier
from app.models.alerte import Alerte
from app.models.audit import AuditLog
from app.repositories import audit_repo

router = APIRouter(prefix="/rapports", tags=["rapports"])


def _s(text: str) -> str:
    return (text or "").replace("—", "-").replace("–", "-").encode("latin-1", errors="replace").decode("latin-1")


def _generate_pdf(title: str, meta: str, sections: list[tuple[str, list[list[str]], list[str]]]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_fill_color(26, 46, 74)
    pdf.set_text_color(232, 184, 75)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, _s(title), ln=True, fill=True, align="C")
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, _s(meta), ln=True, align="C")
    pdf.set_text_color(220, 38, 38)
    pdf.cell(0, 5, "CONFIDENTIEL - Usage interne uniquement (Art. 63)", ln=True, align="C")

    for heading, rows, headers in sections:
        pdf.ln(5)
        pdf.set_text_color(232, 184, 75)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, _s(heading), ln=True)
        if headers:
            col_w = [190 // len(headers)] * len(headers)
            pdf.set_fill_color(26, 46, 74)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 8)
            for w, h in zip(col_w, headers):
                pdf.cell(w, 7, _s(h), fill=True, align="C")
            pdf.ln()
        else:
            col_w = [190]
        pdf.set_font("Helvetica", "", 8)
        for i, row in enumerate(rows):
            pdf.set_fill_color(248, 250, 252) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(30, 41, 59)
            for w, v in zip(col_w, row):
                pdf.cell(w, 6, _s(str(v))[:50], fill=True)
            pdf.ln()
        if not rows:
            pdf.set_text_color(148, 163, 184)
            pdf.cell(0, 6, "Aucune donnee.", ln=True)

    return bytes(pdf.output())


@router.post("/conformite")
async def rapport_conformite(
    body: dict,
    request: Request,
    actor: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Rapport de conformité périodique."""
    date_debut = body.get("date_debut", "")
    date_fin = body.get("date_fin", "")
    periode = f"{date_debut} -> {date_fin}" if date_debut and date_fin else "Toutes periodes"

    total_dossiers = (await db.execute(select(func.count()).select_from(Dossier))).scalar_one()
    by_class = (await db.execute(
        select(Dossier.classification, func.count()).group_by(Dossier.classification)
    )).all()
    by_statut = (await db.execute(
        select(Dossier.statut, func.count()).group_by(Dossier.statut)
    )).all()
    alertes_ouvertes = (await db.execute(
        select(func.count()).select_from(Alerte).where(Alerte.statut == "ouverte")
    )).scalar_one()

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    meta = f"Genere le {generated_at} par {actor.first_name} {actor.last_name} ({actor.role}) - Periode: {periode}"

    sections = [
        ("Synthese", [
            ["Total dossiers actifs", str(total_dossiers)],
            ["Alertes ouvertes", str(alertes_ouvertes)],
        ], ["Indicateur", "Valeur"]),
        ("Repartition par classification", [
            [c or "Non evalue", str(n)] for c, n in by_class
        ], ["Classification", "Nombre"]),
        ("Repartition par statut", [
            [s or "-", str(n)] for s, n in by_statut
        ], ["Statut", "Nombre"]),
    ]

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="rapport.conformite_exported",
        user_id=actor.id, user_role=actor.role,
        entity_type="rapport", entity_id="conformite", ip=ip,
        detail={"periode_debut": date_debut, "periode_fin": date_fin},
    )
    pdf = _generate_pdf("Rapport de Conformite LBC/FT/FP", meta, sections)
    filename = f"rapport-conformite-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/client")
async def rapport_client(
    body: dict,
    request: Request,
    actor: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Rapport dossier complet — sans info DOS (Art. 63)."""
    ref = body.get("dossier_reference", "").strip()
    if not ref:
        raise HTTPException(status_code=422, detail="Reference dossier obligatoire.")

    result = await db.execute(select(Dossier).where(Dossier.reference == ref))
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Dossier {ref} introuvable.")

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    meta = f"Genere le {generated_at} par {actor.first_name} {actor.last_name} ({actor.role})"

    rows = [
        ["Reference", dossier.reference],
        ["Type client", dossier.type_client or "-"],
        ["Nature operation", dossier.type_operation or "-"],
        ["Statut", dossier.statut or "-"],
        ["Classification", dossier.classification or "Non evalue"],
        ["Score", f"{dossier.score_base}/20" if dossier.score_base is not None else "-"],
        ["Trigger actif", dossier.trigger_actif or "Aucun"],
        ["Cree le", dossier.created_at.strftime("%d/%m/%Y") if dossier.created_at else "-"],
    ]

    sections = [("Informations dossier", rows, ["Champ", "Valeur"])]

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="rapport.client_exported",
        user_id=actor.id, user_role=actor.role,
        entity_type="dossier", entity_id=dossier.id, ip=ip,
        detail={"reference": ref},
    )
    pdf = _generate_pdf(f"Rapport Client - {dossier.reference}", meta, sections)
    filename = f"rapport-client-{ref}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/audit")
async def rapport_audit(
    body: dict,
    request: Request,
    actor: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Piste d'audit complète — 500 dernières entrées."""
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)
    logs = list((await db.execute(q)).scalars().all())

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    meta = f"Genere le {generated_at} par {actor.first_name} {actor.last_name} ({actor.role})"

    rows = [
        [
            e.created_at.strftime("%d/%m/%Y %H:%M") if e.created_at else "-",
            (e.action or "")[:40],
            (e.user_id or "-")[:25],
            e.entity_type or "-",
            e.ip_address or "-",
        ]
        for e in logs
    ]
    sections = [(f"Evenements d'audit ({len(logs)} entrees)", rows, ["Date", "Action", "Utilisateur", "Entite", "IP"])]

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="rapport.audit_exported",
        user_id=actor.id, user_role=actor.role,
        entity_type="rapport", entity_id="audit", ip=ip,
        detail={},
    )
    pdf = _generate_pdf("Piste d'Audit Complete", meta, sections)
    filename = f"rapport-audit-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/historique")
async def historique_rapports(
    actor: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Historique des rapports générés (reconstruit depuis la piste d'audit).

    Les PDF sont streamés à la volée (non persistés) → pas de re-téléchargement :
    `download_url` est vide. L'historique reste traçable (type, auteur, date)."""
    rows = (await db.execute(
        select(AuditLog).where(AuditLog.entity_type == "rapport")
        .order_by(AuditLog.created_at.desc()).limit(100)
    )).scalars().all()
    user_ids = {r.user_id for r in rows if r.user_id}
    names: dict[str, str] = {}
    if user_ids:
        urows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        names = {u.id: getattr(u, "full_name", None) or f"{u.first_name} {u.last_name}".strip() for u in urows}
    items = []
    for r in rows:
        detail = r.detail if isinstance(r.detail, dict) else {}
        items.append({
            "id": r.id,
            "type_rapport": (r.entity_id or "—").capitalize(),
            "reference": detail.get("reference") or detail.get("dossier_reference") or "—",
            "generated_by": names.get(r.user_id, r.user_id or "—"),
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "download_url": "",
        })
    return {"items": items}
