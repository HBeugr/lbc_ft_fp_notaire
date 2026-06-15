"""
Router DOS — Déclarations d'Opérations Suspectes.

Règles Art. 63 — Confidentialité absolue :
  - Aucun rôle ne peut révéler l'existence d'une DOS au client
  - Accès restreint : responsable_conformite + notaire_principal + admin (require_rc)
  - Le statut 'DOS en cours' sur le dossier ne doit pas apparaître dans les documents clients
"""
import uuid
from datetime import datetime, timezone, timedelta, date as date_cls
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_rc
from app.models.dos import DeclarationSuspicion, DosAddendum
from app.models.user import User
from app.repositories import dos_repo, dossier_repo, audit_repo, alertes_repo
from app.schemas.dos import (
    AddendumCreate, AddendumOut, DosAccuseRequest, DosClasserRequest,
    DosCreate, DosOut, DosUpsert,
)

router = APIRouter(prefix="/dos", tags=["dos"])

# Confidentialité Art. 63 — accès DOS restreint. Le Déclarant CENTIF prépare la DOS ;
# le RC (responsable_conformite) valide la conformité ; le DG (notaire_principal) autorise
# et transmet à la CENTIF (double validation distincte, Art. 100).
_DOS_ACCESS_ROLES = {"admin", "notaire_principal", "responsable_conformite", "declarant_centif"}
_DELAI_ACCUSE_JOURS = 15


async def require_dos_access(user: User = Depends(get_current_user)) -> User:
    if user.role not in _DOS_ACCESS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux acteurs de la déclaration (Art. 63).",
        )
    return user


def _ref() -> str:
    return f"DOS-{uuid.uuid4().hex[:10].upper()}"


async def run_dos_accuse_check(db: AsyncSession) -> None:
    """Alerte J+15 — DOS transmise sans accusé de réception CENTIF (Art. 79)."""
    seuil = datetime.now(timezone.utc) - timedelta(days=_DELAI_ACCUSE_JOURS)
    result = await db.execute(
        select(DeclarationSuspicion).where(
            DeclarationSuspicion.statut == "transmise",
            DeclarationSuspicion.accuse_recu_at.is_(None),
            DeclarationSuspicion.accuse_alerte_j15_envoyee.is_(False),
            DeclarationSuspicion.date_transmission_centif < seuil,
        )
    )
    for dos in result.scalars().all():
        await alertes_repo.create(
            db,
            dossier_id=dos.dossier_id,
            type_alerte="DOS_ACCUSE_J15",
            niveau="MOYEN",
            statut="ouverte",
            description=f"DOS {dos.reference_interne} transmise sans accusé de réception CENTIF depuis plus de {_DELAI_ACCUSE_JOURS} jours.",
        )
        await dos_repo.update(db, dos, accuse_alerte_j15_envoyee=True)


async def _get_dos_or_404(db: AsyncSession, dos_id: str) -> DeclarationSuspicion:
    dos = await dos_repo.get_by_id(db, dos_id)
    if not dos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DOS introuvable.")
    return dos


async def _dos_with_addendums(db: AsyncSession, dos: DeclarationSuspicion) -> DosOut:
    result = await db.execute(
        select(DosAddendum).where(DosAddendum.dos_id == dos.id).order_by(DosAddendum.created_at)
    )
    return DosOut.from_orm_safe(dos, addendums=list(result.scalars().all()))


@router.get("", response_model=list[DosOut])
async def list_dos(
    _: User = Depends(require_dos_access),
    db: AsyncSession = Depends(get_db),
    statut: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[DosOut]:
    await run_dos_accuse_check(db)
    dos_list = await dos_repo.list_all(db, limit=limit, offset=offset)
    if statut:
        dos_list = [d for d in dos_list if d.statut == statut]
    result = []
    for dos in dos_list:
        add_result = await db.execute(select(DosAddendum).where(DosAddendum.dos_id == dos.id))
        result.append(DosOut.from_orm_safe(dos, addendums=list(add_result.scalars().all())))
    return result


@router.post("", response_model=DosOut, status_code=status.HTTP_201_CREATED)
async def create_dos(
    body: DosCreate,
    request: Request,
    current_user: User = Depends(require_dos_access),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    dossier = await dossier_repo.get_by_id(db, body.dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    existing = await dos_repo.get_by_dossier(db, body.dossier_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une DOS existe déjà pour ce dossier.")
    dos = await dos_repo.create(
        db,
        dossier_id=body.dossier_id,
        reference_interne=_ref(),
        initie_par=current_user.id,
    )
    # Blocage automatique du dossier à la création de la DOS (mesure conservatoire) + alerte
    if not dossier.is_bloque or dossier.statut != "bloque":
        dossier.is_bloque = True
        await dossier_repo.update_statut(
            db, dossier, "bloque", current_user.id,
            commentaire="Blocage automatique — déclaration d'opération suspecte ouverte.",
        )
        await alertes_repo.create(
            db,
            dossier_id=dossier.id,
            type_alerte="DOSSIER_BLOQUE",
            niveau="ELEVE",
            statut="ouverte",
            description=f"Dossier bloqué automatiquement — DOS {dos.reference_interne} ouverte.",
        )
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.created",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos.id,
        ip=ip,
        detail={"reference": dos.reference_interne, "dossier_id": body.dossier_id},
    )
    return DosOut.from_orm_safe(dos)


@router.get("/{dos_id}", response_model=DosOut)
async def get_dos(
    dos_id: str,
    _: User = Depends(require_dos_access),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    dos = await _get_dos_or_404(db, dos_id)
    return await _dos_with_addendums(db, dos)


# Statuts à partir desquels la DOS n'est plus modifiable (utiliser un addendum)
_DOS_VERROUILLEE = ("soumis", "transmise", "classee", "accuse_recu")


@router.put("/{dos_id}", response_model=DosOut)
async def update_dos(
    dos_id: str,
    body: DosUpsert,
    request: Request,
    current_user: User = Depends(require_dos_access),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut in _DOS_VERROUILLEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DOS verrouillée — utiliser un addendum pour la compléter."
        )
    data = body.model_dump(exclude_none=True)
    if "date_detection" in data and data["date_detection"]:
        try:
            data["date_detection"] = date_cls.fromisoformat(str(data["date_detection"])[:10])
        except ValueError:
            data.pop("date_detection")
    for field in ("motifs", "statut_operations", "supports", "relations_affaires"):
        if field in data and data[field] is not None and not isinstance(data[field], dict):
            data[field] = data[field].model_dump() if hasattr(data[field], "model_dump") else dict(data[field])
    if "detail_transactions" in data and isinstance(data["detail_transactions"], list):
        data["detail_transactions"] = [
            t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in data["detail_transactions"]
        ]
    dos = await dos_repo.update(db, dos, **data)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.updated",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos_id,
        ip=ip,
    )
    return await _dos_with_addendums(db, dos)


async def _audit(db, action, user, dos_id, ip, detail=None):
    await audit_repo.log(
        db, action=action, user_id=user.id, user_role=user.role,
        entity_type="dos", entity_id=dos_id, ip=ip, detail=detail,
    )


@router.post("/{dos_id}/soumettre", response_model=DosOut)
async def soumettre_dos(
    dos_id: str,
    request: Request,
    current_user: User = Depends(require_dos_access),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Soumet la DOS au circuit de validation (Déclarant → RC). Au moins un type de soupçon requis."""
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut not in ("brouillon", "en_cours", "en_validation"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="DOS déjà engagée dans le circuit de validation.")
    if not (dos.type_soupcon_bc or dos.type_soupcon_ft or dos.type_soupcon_prolif):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sélectionner au moins un type de soupçon (Blanchiment / FT / Prolifération) avant de soumettre."
        )
    dos = await dos_repo.update(db, dos, statut="en_validation")
    ip = request.client.host if request.client else "unknown"
    await _audit(db, "dos.soumise_validation", current_user, dos_id, ip, {"reference": dos.reference_interne})
    return await _dos_with_addendums(db, dos)


@router.post("/{dos_id}/valider", response_model=DosOut)
async def valider_dos(
    dos_id: str,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Validation conformité par le Responsable Conformité (1re validation, Art. 100)."""
    if current_user.role not in ("responsable_conformite", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Validation réservée au Responsable Conformité.")
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut not in ("en_validation", "soumis"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La DOS doit être soumise pour être validée.")
    dos = await dos_repo.update(
        db, dos,
        statut="validee_rc",
        valide_par_rc=current_user.id,
        valide_rc_at=datetime.now(timezone.utc),
        valide_par=current_user.id,
    )
    ip = request.client.host if request.client else "unknown"
    await _audit(db, "dos.validee_rc", current_user, dos_id, ip, {"reference": dos.reference_interne})
    return await _dos_with_addendums(db, dos)


@router.post("/{dos_id}/transmettre", response_model=DosOut)
async def transmettre_dos(
    dos_id: str,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Autorisation finale + transmission CENTIF par le Notaire Principal (DG, Art. 100).
    Le signataire doit être distinct du Responsable Conformité ayant validé."""
    if current_user.role not in ("notaire_principal", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Transmission réservée au Notaire Principal.")
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut != "validee_rc":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La DOS doit être validée par la conformité avant transmission.")
    if dos.valide_par_rc and dos.valide_par_rc == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Séparation des fonctions (Art. 100) : le signataire de la transmission doit être distinct du valideur conformité.",
        )
    now = datetime.now(timezone.utc)
    dos = await dos_repo.update(
        db, dos,
        statut="transmise",
        decision="transmettre",
        valide_par_dg=current_user.id,
        valide_dg_at=now,
        date_transmission_centif=now,
        transmis_par=current_user.id,
        soumis_at=now,
    )
    ip = request.client.host if request.client else "unknown"
    await _audit(db, "dos.transmise", current_user, dos_id, ip, {"reference": dos.reference_interne})
    return await _dos_with_addendums(db, dos)


@router.post("/{dos_id}/classer", response_model=DosOut)
async def classer_dos(
    dos_id: str,
    body: DosClasserRequest,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Classement sans suite, motivé (RC ou Notaire Principal)."""
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut not in ("en_validation", "validee_rc", "soumis"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seule une DOS en cours de validation peut être classée.")
    if not body.motif.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Un motif de classement est obligatoire.")
    dos = await dos_repo.update(
        db, dos,
        statut="classee",
        decision="classer",
        motif_classement=body.motif.strip(),
    )
    ip = request.client.host if request.client else "unknown"
    await _audit(db, "dos.classee", current_user, dos_id, ip, {"reference": dos.reference_interne, "motif": body.motif.strip()})
    return await _dos_with_addendums(db, dos)


@router.patch("/{dos_id}/accuse-recu", response_model=DosOut)
async def accuse_recu_dos(
    dos_id: str,
    reference_centif: str,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> DosOut:
    """Enregistre l'accusé de réception CENTIF (après transmission)."""
    dos = await _get_dos_or_404(db, dos_id)
    if dos.statut not in ("transmise", "soumis"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La DOS doit être transmise avant d'enregistrer un accusé.")
    dos = await dos_repo.update(
        db, dos,
        statut="accuse_recu",
        accuse_recu_ref=reference_centif,
        accuse_recu_at=datetime.now(timezone.utc),
    )
    ip = request.client.host if request.client else "unknown"
    await _audit(db, "dos.accuse_recu", current_user, dos_id, ip, {"reference_centif": reference_centif})
    return await _dos_with_addendums(db, dos)


@router.post("/{dos_id}/addendums", response_model=AddendumOut, status_code=status.HTTP_201_CREATED)
async def add_addendum(
    dos_id: str,
    body: AddendumCreate,
    request: Request,
    current_user: User = Depends(require_dos_access),
    db: AsyncSession = Depends(get_db),
) -> AddendumOut:
    """Complément d'information — append-only, même après soumission."""
    await _get_dos_or_404(db, dos_id)
    addendum = await dos_repo.add_addendum(db, dos_id, current_user.id, body.contenu)
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="dos.addendum_added",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="dos",
        entity_id=dos_id,
        ip=ip,
    )
    return AddendumOut.from_orm_safe(addendum)


def _pdf_txt(text) -> str:
    return (str(text) if text is not None else "").replace("—", "-").replace("–", "-").encode("latin-1", errors="replace").decode("latin-1")


def _generate_dos_pdf(dos: DeclarationSuspicion) -> bytes:
    """PDF confidentiel de la DOS (Art. 63) — 10 sections CENTIF."""
    from fpdf import FPDF

    soupcons = [lbl for flag, lbl in (
        (dos.type_soupcon_bc, "Blanchiment de capitaux"),
        (dos.type_soupcon_ft, "Financement du terrorisme"),
        (dos.type_soupcon_prolif, "Financement de la prolifération"),
    ) if flag]

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_fill_color(26, 46, 74)
    pdf.set_text_color(232, 184, 75)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, _pdf_txt(f"Declaration d'Operation Suspecte - {dos.reference_interne}"), ln=True, fill=True, align="C")
    pdf.set_text_color(220, 38, 38)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, "CONFIDENTIEL - Art. 63 - Interdiction de divulgation au client (peine penale)", ln=True, align="C")
    pdf.ln(2)

    def section(title, lines):
        pdf.set_fill_color(26, 46, 74)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, _pdf_txt(title), ln=True, fill=True)
        pdf.set_text_color(30, 41, 59)
        pdf.set_font("Helvetica", "", 8)
        for line in lines:
            pdf.multi_cell(0, 5, _pdf_txt(line))
        pdf.ln(1)

    section("1. Organisme declarant", [
        f"Cabinet : {dos.organisme_libelle or '-'}", f"Adresse : {dos.organisme_adresse or '-'}",
        f"Email : {dos.organisme_email or '-'}", f"Telephone : {dos.organisme_telephone or '-'}",
    ])
    section("2. Informations generales", [
        f"Reference interne : {dos.reference_interne}", f"Statut : {dos.statut}",
        f"Date de detection : {dos.date_detection.isoformat() if dos.date_detection else '-'}",
    ])
    section("3. Analyse - Type de soupcon", [f"Type(s) : {', '.join(soupcons) or '-'}"])
    section("3b. Motifs (CENTIF)", [", ".join(k for k, v in (dos.motifs or {}).items() if v is True) or "-"])
    section("4. Statut des operations", [
        f"Nature de l'operation : {dos.statut_operation or '-'}",
        f"Detail : {(dos.statut_operations or {})}",
    ])
    section("5. Detail des transactions", [f"{dos.detail_transactions or '-'}"])
    section("6. Indices de blanchiment", [dos.indices_blanchiment or "-"])
    section("7. Identification des intervenants", [f"{dos.identification or '-'}"])
    section("8. Relations d'affaires", [f"{dos.relations_affaires or '-'}"])
    section("9. Supports utilises", [f"{dos.supports or '-'}"])
    section("10. Autres informations", [dos.autres_informations or "-"])
    section("Decision / Transmission", [
        f"Decision : {dos.decision or '-'}", f"Motif de classement : {dos.motif_classement or '-'}",
        f"Transmise CENTIF le : {dos.date_transmission_centif.isoformat() if dos.date_transmission_centif else '-'}",
        f"Accuse de reception : {dos.accuse_recu_ref or '-'}",
    ])
    return bytes(pdf.output())


@router.get("/{dos_id}/pdf")
async def export_dos_pdf(
    dos_id: str,
    request: Request,
    current_user: User = Depends(require_rc),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export PDF du DOS (DOS-05) — reserve a l'Admin et au Notaire Principal (Art. 63)."""
    if current_user.role not in ("admin", "notaire_principal"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'export PDF d'une DOS est reserve au Notaire Principal et a l'Administrateur.",
        )
    dos = await _get_dos_or_404(db, dos_id)
    pdf_bytes = _generate_dos_pdf(dos)
    ip = request.client.host if request.client else "unknown"
    await _audit(db, "dos.pdf_exported", current_user, dos_id, ip, {"reference": dos.reference_interne})
    filename = f"DOS-{dos.reference_interne}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
