"""Documents KYC — métadonnées persistées (table `documents`) + intégrité SHA-256,
validation magic-bytes, stockage MinIO. Accès API uniquement (jamais d'URL directe).

Endpoints (alignés sur le frontend) :
  POST   /dossiers/{dossier_id}/documents   — upload (file + type_document)
  GET    /dossiers/{dossier_id}/documents   — liste des documents (non supprimés)
  GET    /documents/{doc_id}/download       — stream depuis MinIO
  DELETE /documents/{doc_id}                — soft-delete (superviseur)
"""
import hashlib
import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.storage import ensure_current_tenant_bucket, get_minio_client, tenant_bucket
from app.core.uploads import ensure_allowed_upload
from app.models.document import Document
from app.models.user import User
from app.repositories import dossier_repo, audit_repo

router = APIRouter(tags=["documents"])

_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 Mo


class DocumentOut(BaseModel):
    id: str
    dossier_id: str
    nom_fichier: str
    type_document: str
    taille_octets: int
    created_at: str


def _out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id, dossier_id=d.dossier_id, nom_fichier=d.nom_fichier,
        type_document=d.type_document, taille_octets=d.taille_octets,
        created_at=d.created_at.isoformat() if d.created_at else "",
    )


def _safe_header_filename(name: str) -> str:
    cleaned = "".join(c if (c.isalnum() or c in " ._-") else "_" for c in (name or "document"))
    return cleaned[:255] or "document"


async def _assert_access(db: AsyncSession, dossier_id: str, user: User):
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable.")
    if not user.is_supervisor and dossier.assigned_to != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    return dossier


@router.post("/dossiers/{dossier_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    dossier_id: str,
    request: Request,
    file: UploadFile = File(...),
    type_document: str = Form("autre"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    await _assert_access(db, dossier_id, current_user)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Fichier trop volumineux (max 20 Mo).")
    # Défense en profondeur : extension + content-type + magic-bytes (anti-fichier déguisé)
    ensure_allowed_upload(file.filename, file.content_type, content)

    safe_filename = os.path.basename(file.filename or "document")
    ext = Path(safe_filename).suffix.lower()
    doc_id = str(uuid.uuid4())
    minio_key = f"dossiers/{dossier_id}/{doc_id}{ext}"
    sha256 = hashlib.sha256(content).hexdigest()
    content_type = file.content_type or "application/octet-stream"

    try:
        # Filet de sécurité si le bucket du cabinet n'a pas survécu au provisioning.
        bucket = ensure_current_tenant_bucket()
        get_minio_client().put_object(
            bucket, minio_key, io.BytesIO(content), length=len(content), content_type=content_type
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erreur de stockage : {type(exc).__name__}.")

    doc = Document(
        id=doc_id, dossier_id=dossier_id, type_document=type_document or "autre",
        nom_fichier=safe_filename, minio_key=minio_key, content_type=content_type,
        taille_octets=len(content), sha256_hash=sha256, uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="document.uploaded", user_id=current_user.id, user_role=current_user.role,
        entity_type="document", entity_id=doc_id, ip=ip,
        detail={"dossier_id": dossier_id, "nom_fichier": safe_filename, "type_document": type_document, "sha256": sha256, "taille_octets": len(content)},
    )
    return _out(doc)


@router.get("/dossiers/{dossier_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    dossier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    await _assert_access(db, dossier_id, current_user)
    rows = (await db.execute(
        select(Document).where(Document.dossier_id == dossier_id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )).scalars().all()
    return [_out(d) for d in rows]


async def _get_doc_or_404(db: AsyncSession, doc_id: str) -> Document:
    doc = (await db.execute(
        select(Document).where(Document.id == doc_id, Document.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    return doc


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    doc = await _get_doc_or_404(db, doc_id)
    await _assert_access(db, doc.dossier_id, current_user)
    try:
        response = get_minio_client().get_object(tenant_bucket(), doc.minio_key)
        content = response.read()
        response.close()
        response.release_conn()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erreur de récupération : {type(exc).__name__}.")
    return Response(
        content=content,
        media_type=doc.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{_safe_header_filename(doc.nom_fichier)}"'},
    )


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Suppression (soft-delete) — réservée aux superviseurs."""
    if not current_user.is_supervisor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Suppression réservée aux superviseurs.")
    doc = await _get_doc_or_404(db, doc_id)
    doc.deleted_at = datetime.now(timezone.utc)
    db.add(doc)
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db, action="document.deleted", user_id=current_user.id, user_role=current_user.role,
        entity_type="document", entity_id=doc_id, ip=ip,
        detail={"dossier_id": doc.dossier_id, "nom_fichier": doc.nom_fichier},
    )
