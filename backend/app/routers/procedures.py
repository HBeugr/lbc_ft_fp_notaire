"""
Procédures router — Référentiel institutionnel « Mes Procédures ».

Une procédure = un nom + jusqu'à 7 pièces jointes (slots 1 à 7).
Fichiers stockés dans MinIO (bucket documents), intégrité SHA-256 inline.
Accessible à tous les rôles internes (lecture + gestion).

Endpoints:
  POST   /api/procedures                          — créer une procédure
  GET    /api/procedures                          — liste paginée + filtrable (search)
  GET    /api/procedures/{procedure_id}           — détail + ses 7 slots
  PATCH  /api/procedures/{procedure_id}           — renommer
  DELETE /api/procedures/{procedure_id}           — soft-delete (+ ses pièces)
  POST   /api/procedures/{procedure_id}/files     — upload sur un slot (1..7) + SHA-256
  GET    /api/procedure-files/{file_id}/download  — stream depuis MinIO
  DELETE /api/procedure-files/{file_id}           — soft-delete d'une pièce
"""
import hashlib
import io
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.storage import ensure_current_tenant_bucket, get_minio_client, tenant_bucket
from app.core.uploads import sniff_signature
from app.models.user import User
from app.repositories import audit_repo

router = APIRouter(tags=["procedures"])

NB_SLOTS = 7
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 Mo (aligné sur documents.py)

# Formats de pièces acceptés (PDF, JPG/JPEG, PNG)
ACCEPTED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
ACCEPTED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
# Signatures réelles autorisées (magic-bytes) — les seules qui fassent foi.
ACCEPTED_SIGNATURE_FAMILIES = frozenset({"pdf", "jpeg", "png"})


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProcedureCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=255)


class ProcedureUpdate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=255)


class ProcedureFileOut(BaseModel):
    id: str
    procedure_id: str
    slot: int
    nom_fichier: str
    taille_octets: int
    sha256_hash: str
    uploaded_by: str
    created_at: datetime


class ProcedureOut(BaseModel):
    id: str
    nom: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    nb_pieces: int


class ProcedureDetail(ProcedureOut):
    files: list[ProcedureFileOut]


class ProcedureListResponse(BaseModel):
    items: list[ProcedureOut]
    total: int
    page: int
    page_size: int


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _safe_header_filename(name: str) -> str:
    """Neutralise CR/LF/guillemets pour éviter l'injection d'en-tête HTTP (Content-Disposition)."""
    cleaned = "".join(c if (c.isalnum() or c in " ._-") else "_" for c in (name or "fichier"))
    return cleaned[:255] or "fichier"


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/procedures", response_model=ProcedureOut, status_code=status.HTTP_201_CREATED)
async def create_procedure(
    payload: ProcedureCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> ProcedureOut:
    proc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        text("""
            INSERT INTO procedures (id, nom, created_by, created_at, updated_at)
            VALUES (:id, :nom, :created_by, :created_at, :updated_at)
        """),
        {
            "id": proc_id,
            "nom": payload.nom.strip(),
            "created_by": actor.id,
            "created_at": now,
            "updated_at": now,
        },
    )
    await audit_repo.log(
        db,
        action="procedure.created",
        user_id=actor.id,
        user_role=actor.role,
        entity_type="procedure",
        entity_id=proc_id,
        ip=_ip(request),
        detail={"nom": payload.nom.strip()},
    )
    await db.commit()
    return ProcedureOut(
        id=proc_id,
        nom=payload.nom.strip(),
        created_by=actor.id,
        created_at=now,
        updated_at=now,
        nb_pieces=0,
    )


# ── List (paginée + filtrable) ────────────────────────────────────────────────
# Requêtes pré-construites en littéraux (aucune interpolation de données utilisateur :
# le filtre passe par le paramètre lié :search). Évite tout vecteur d'injection SQL.
_SELECT_LIST = (
    "SELECT p.id, p.nom, p.created_by, p.created_at, p.updated_at, "
    "(SELECT COUNT(*) FROM procedure_documents d "
    " WHERE d.procedure_id = p.id AND d.deleted_at IS NULL) AS nb_pieces "
    "FROM procedures p WHERE p.deleted_at IS NULL"
)
_ORDER_PAGE = " ORDER BY p.created_at DESC LIMIT :limit OFFSET :offset"
_SEARCH_CLAUSE = " AND LOWER(p.nom) LIKE :search"

# nosec : concaténation de littéraux uniquement (aucune donnée utilisateur ; filtre via param lié :search)
_COUNT_SQL = text("SELECT COUNT(*) AS c FROM procedures p WHERE p.deleted_at IS NULL")
_COUNT_SQL_SEARCH = text("SELECT COUNT(*) AS c FROM procedures p WHERE p.deleted_at IS NULL" + _SEARCH_CLAUSE)  # nosec B608
_LIST_SQL = text(_SELECT_LIST + _ORDER_PAGE)  # nosec B608
_LIST_SQL_SEARCH = text(_SELECT_LIST + _SEARCH_CLAUSE + _ORDER_PAGE)  # nosec B608


@router.get("/procedures", response_model=ProcedureListResponse)
async def list_procedures(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> ProcedureListResponse:
    has_search = bool(search and search.strip())
    params: dict = {}
    if has_search:
        params["search"] = f"%{search.strip().lower()}%"

    total_row = await db.execute(_COUNT_SQL_SEARCH if has_search else _COUNT_SQL, params)
    total = total_row.scalar() or 0

    params_page = {**params, "limit": page_size, "offset": (page - 1) * page_size}
    rows = await db.execute(_LIST_SQL_SEARCH if has_search else _LIST_SQL, params_page)
    items = [
        ProcedureOut(
            id=r.id,
            nom=r.nom,
            created_by=r.created_by,
            created_at=r.created_at,
            updated_at=r.updated_at,
            nb_pieces=r.nb_pieces,
        )
        for r in rows
    ]
    return ProcedureListResponse(items=items, total=total, page=page, page_size=page_size)


# ── Detail ────────────────────────────────────────────────────────────────────

async def _get_procedure_or_404(db: AsyncSession, procedure_id: str):
    row = await db.execute(
        text("""
            SELECT id, nom, created_by, created_at, updated_at
            FROM procedures WHERE id = :id AND deleted_at IS NULL
        """),
        {"id": procedure_id},
    )
    proc = row.first()
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procédure introuvable.")
    return proc


@router.get("/procedures/{procedure_id}", response_model=ProcedureDetail)
async def get_procedure(
    procedure_id: str,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> ProcedureDetail:
    proc = await _get_procedure_or_404(db, procedure_id)
    rows = await db.execute(
        text("""
            SELECT id, procedure_id, slot, nom_fichier, taille_octets,
                   sha256_hash, uploaded_by, created_at
            FROM procedure_documents
            WHERE procedure_id = :id AND deleted_at IS NULL
            ORDER BY slot ASC
        """),
        {"id": procedure_id},
    )
    files = [
        ProcedureFileOut(
            id=r.id,
            procedure_id=r.procedure_id,
            slot=r.slot,
            nom_fichier=r.nom_fichier,
            taille_octets=r.taille_octets,
            sha256_hash=r.sha256_hash,
            uploaded_by=r.uploaded_by,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ProcedureDetail(
        id=proc.id,
        nom=proc.nom,
        created_by=proc.created_by,
        created_at=proc.created_at,
        updated_at=proc.updated_at,
        nb_pieces=len(files),
        files=files,
    )


# ── Rename ────────────────────────────────────────────────────────────────────

@router.patch("/procedures/{procedure_id}", response_model=ProcedureOut)
async def update_procedure(
    procedure_id: str,
    payload: ProcedureUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> ProcedureOut:
    proc = await _get_procedure_or_404(db, procedure_id)
    now = datetime.now(timezone.utc)
    await db.execute(
        text("UPDATE procedures SET nom = :nom, updated_at = :now WHERE id = :id"),
        {"nom": payload.nom.strip(), "now": now, "id": procedure_id},
    )
    await audit_repo.log(
        db,
        action="procedure.updated",
        user_id=actor.id,
        user_role=actor.role,
        entity_type="procedure",
        entity_id=procedure_id,
        ip=_ip(request),
        detail={"nom": payload.nom.strip(), "nom_precedent": proc.nom},
    )
    await db.commit()
    nb_row = await db.execute(
        text("SELECT COUNT(*) FROM procedure_documents WHERE procedure_id = :id AND deleted_at IS NULL"),
        {"id": procedure_id},
    )
    return ProcedureOut(
        id=procedure_id,
        nom=payload.nom.strip(),
        created_by=proc.created_by,
        created_at=proc.created_at,
        updated_at=now,
        nb_pieces=nb_row.scalar() or 0,
    )


# ── Delete (soft) ─────────────────────────────────────────────────────────────

@router.delete("/procedures/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procedure(
    procedure_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> None:
    proc = await _get_procedure_or_404(db, procedure_id)
    now = datetime.now(timezone.utc)
    await db.execute(
        text("UPDATE procedures SET deleted_at = :now WHERE id = :id"),
        {"now": now, "id": procedure_id},
    )
    await db.execute(
        text("UPDATE procedure_documents SET deleted_at = :now WHERE procedure_id = :id AND deleted_at IS NULL"),
        {"now": now, "id": procedure_id},
    )
    await audit_repo.log(
        db,
        action="procedure.deleted",
        user_id=actor.id,
        user_role=actor.role,
        entity_type="procedure",
        entity_id=procedure_id,
        ip=_ip(request),
        detail={"nom": proc.nom},
    )
    await db.commit()


# ── Upload pièce (slot 1..7) ──────────────────────────────────────────────────

@router.post(
    "/procedures/{procedure_id}/files",
    response_model=ProcedureFileOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_procedure_file(
    procedure_id: str,
    request: Request,
    file: UploadFile = File(...),
    slot: int = Form(...),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> ProcedureFileOut:
    """Dépose une pièce sur un slot (1..7). Remplace la pièce existante du slot."""
    if slot < 1 or slot > NB_SLOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slot invalide (doit être entre 1 et {NB_SLOTS}).",
        )
    await _get_procedure_or_404(db, procedure_id)

    # Validation du format (PDF, JPG/JPEG, PNG)
    filename = file.filename or ""
    ext_ok = filename.lower().endswith(ACCEPTED_EXTENSIONS)
    type_ok = (file.content_type or "").lower() in ACCEPTED_CONTENT_TYPES
    if not (ext_ok or type_ok):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format non autorisé. Seuls les fichiers PDF, JPG/JPEG et PNG sont acceptés.",
        )

    # Limite de taille (anti-DoS mémoire) — vérifiée avant et après lecture
    if file.size is not None and file.size > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 20 Mo).",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 20 Mo).",
        )
    # Le format déclaré (nom + content-type) est déclaratif : seule la signature
    # réelle du contenu fait foi. Refuse un fichier déguisé (HTML/script renommé .pdf).
    if sniff_signature(content) not in ACCEPTED_SIGNATURE_FAMILIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contenu ne correspondant pas au format déclaré (fichier déguisé).",
        )

    sha256_hash = hashlib.sha256(content).hexdigest()
    file_id = str(uuid.uuid4())
    # basename + neutralisation des séparateurs : la clé de stockage ne doit pas
    # pouvoir échapper au préfixe de la procédure via « ../ » dans le nom de fichier.
    safe_name = os.path.basename(file.filename or "fichier").replace(" ", "_") or "fichier"
    minio_key = f"procedures/{procedure_id}/{slot}/{file_id}/{safe_name}"
    content_type = file.content_type or "application/octet-stream"

    try:
        # Filet de sécurité si le bucket du cabinet n'a pas survécu au provisioning.
        bucket = ensure_current_tenant_bucket()
        get_minio_client().put_object(
            bucket,
            minio_key,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
    except S3Error as exc:
        # Ne pas divulguer les détails internes du stockage (bucket, clé, endpoint).
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur de stockage : {type(exc).__name__}.",
        )

    now = datetime.now(timezone.utc)

    # Remplacement : soft-delete la pièce active déjà présente sur ce slot
    await db.execute(
        text("""
            UPDATE procedure_documents SET deleted_at = :now
            WHERE procedure_id = :pid AND slot = :slot AND deleted_at IS NULL
        """),
        {"now": now, "pid": procedure_id, "slot": slot},
    )

    await db.execute(
        text("""
            INSERT INTO procedure_documents
                (id, procedure_id, slot, nom_fichier, minio_key, taille_octets,
                 sha256_hash, uploaded_by, created_at)
            VALUES
                (:id, :procedure_id, :slot, :nom_fichier, :minio_key, :taille_octets,
                 :sha256_hash, :uploaded_by, :created_at)
        """),
        {
            "id": file_id,
            "procedure_id": procedure_id,
            "slot": slot,
            "nom_fichier": safe_name,
            "minio_key": minio_key,
            "taille_octets": len(content),
            "sha256_hash": sha256_hash,
            "uploaded_by": actor.id,
            "created_at": now,
        },
    )
    await audit_repo.log(
        db,
        action="procedure.file_uploaded",
        user_id=actor.id,
        user_role=actor.role,
        entity_type="procedure",
        entity_id=procedure_id,
        ip=_ip(request),
        detail={"slot": slot, "nom_fichier": safe_name, "sha256": sha256_hash, "taille_octets": len(content)},
    )
    await db.commit()

    return ProcedureFileOut(
        id=file_id,
        procedure_id=procedure_id,
        slot=slot,
        nom_fichier=safe_name,
        taille_octets=len(content),
        sha256_hash=sha256_hash,
        uploaded_by=actor.id,
        created_at=now,
    )


# ── Download pièce ────────────────────────────────────────────────────────────

@router.get("/procedure-files/{file_id}/download")
async def download_procedure_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> StreamingResponse:
    row = await db.execute(
        text("""
            SELECT id, nom_fichier, minio_key
            FROM procedure_documents WHERE id = :id AND deleted_at IS NULL
        """),
        {"id": file_id},
    )
    doc = row.first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce introuvable.")

    try:
        response = get_minio_client().get_object(tenant_bucket(), doc.minio_key)
        data = response.read()
        response.close()
        response.release_conn()
    except S3Error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable dans le stockage.",
        )

    content_type = "application/octet-stream"
    name = doc.nom_fichier.lower()
    if name.endswith(".pdf"):
        content_type = "application/pdf"
    elif name.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif name.endswith(".png"):
        content_type = "image/png"

    safe_name = _safe_header_filename(doc.nom_fichier)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length": str(len(data)),
        },
    )


# ── Delete pièce (soft) ───────────────────────────────────────────────────────

@router.delete("/procedure-files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procedure_file(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> None:
    row = await db.execute(
        text("SELECT id, procedure_id, slot, nom_fichier FROM procedure_documents WHERE id = :id AND deleted_at IS NULL"),
        {"id": file_id},
    )
    doc = row.first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce introuvable.")

    await db.execute(
        text("UPDATE procedure_documents SET deleted_at = :now WHERE id = :id"),
        {"now": datetime.now(timezone.utc), "id": file_id},
    )
    await audit_repo.log(
        db,
        action="procedure.file_deleted",
        user_id=actor.id,
        user_role=actor.role,
        entity_type="procedure",
        entity_id=doc.procedure_id,
        ip=_ip(request),
        detail={"slot": doc.slot, "nom_fichier": doc.nom_fichier},
    )
    await db.commit()
