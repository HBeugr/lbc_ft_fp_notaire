"""Documents — stockage chiffré AES-256, accès API uniquement (jamais par URL directe)."""
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories import dossier_repo, audit_repo

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"}
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 Mo


@router.post("/{dossier_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    dossier_id: str,
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 20 Mo).")

    import os
    from pathlib import Path
    safe_filename = os.path.basename(file.filename or "fichier")
    ext = Path(safe_filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Extension '{ext}' non autorisée.")

    doc_id = str(uuid.uuid4())
    object_name = f"dossiers/{dossier_id}/{doc_id}{ext}"

    from minio import Minio, S3Error
    from app.core.config import settings
    import io

    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        client.put_object(
            settings.MINIO_BUCKET_DOCUMENTS,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Erreur de stockage : {type(exc).__name__}.")

    ip = request.client.host if request.client else "unknown"
    await audit_repo.log(
        db,
        action="document.uploaded",
        user_id=current_user.id,
        user_role=current_user.role,
        entity_type="document",
        entity_id=doc_id,
        ip=ip,
        detail={"dossier_id": dossier_id, "filename": safe_filename, "object_name": object_name},
    )

    return {
        "id": doc_id,
        "dossier_id": dossier_id,
        "filename": safe_filename,
        "object_name": object_name,
        "size_bytes": len(content),
        "description": description,
    }


@router.get("/{dossier_id}/{doc_id}/download")
async def download_document(
    dossier_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    dossier = await dossier_repo.get_by_id(db, dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")
    if not current_user.is_supervisor and dossier.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    # Build object_name — the audit log detail field contains the path
    from sqlalchemy import select
    from app.models.audit import AuditLog
    import json

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == doc_id,
            AuditLog.action == "document.uploaded",
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    detail: dict = json.loads(log.detail) if isinstance(log.detail, str) else (log.detail or {})
    object_name = detail.get("object_name", "")
    filename = detail.get("filename", "document")

    from minio import Minio
    from app.core.config import settings
    import io

    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        response = client.get_object(settings.MINIO_BUCKET_DOCUMENTS, object_name)
        content = response.read()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Erreur de récupération : {type(exc).__name__}.")

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
