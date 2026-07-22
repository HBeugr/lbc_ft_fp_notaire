from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import csv
import io

from app.core.database import get_db
from app.core.deps import require_admin, require_log_reader
from app.models.user import User
from app.repositories import audit_repo

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    user_id: str | None
    user_role: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    ip_address: str | None
    detail: dict | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_safe(cls, obj) -> "AuditLogOut":
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            user_role=obj.user_role,
            action=obj.action,
            entity_type=obj.entity_type,
            entity_id=obj.entity_id,
            ip_address=obj.ip_address,
            detail=obj.detail,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
        )


class AuditLogsResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int


@router.get("/logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    # ADM-06 — Admin + Notaire Principal uniquement (le RC est exclu par le CDC §7.3).
    _: User = Depends(require_log_reader),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None, description="Filtrer par action (ex: user.login)"),
    entity_type: str | None = Query(None, description="Filtrer par type d'entité"),
    entity_id: str | None = Query(None, description="Filtrer par ID d'entité"),
) -> AuditLogsResponse:
    logs = await audit_repo.get_logs(db, limit=limit + 1, offset=offset)
    if action:
        logs = [l for l in logs if l.action == action]
    if entity_type:
        logs = [l for l in logs if l.entity_type == entity_type]
    if entity_id:
        logs = [l for l in logs if l.entity_id == entity_id]
    has_more = len(logs) > limit
    items = logs[:limit]
    return AuditLogsResponse(
        items=[AuditLogOut.from_orm_safe(l) for l in items],
        total=offset + len(items) + (1 if has_more else 0),
        limit=limit,
        offset=offset,
    )


@router.get("/logs/export")
async def export_audit_logs_csv(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
) -> StreamingResponse:
    logs = await audit_repo.get_logs(db, limit=limit, offset=offset)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "created_at", "action", "user_id", "user_role", "entity_type", "entity_id", "ip_address"])
    writer.writeheader()
    for l in logs:
        writer.writerow({
            "id": l.id,
            "created_at": l.created_at.isoformat() if l.created_at else "",
            "action": l.action,
            "user_id": l.user_id or "",
            "user_role": l.user_role or "",
            "entity_type": l.entity_type or "",
            "entity_id": l.entity_id or "",
            "ip_address": l.ip_address or "",
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
