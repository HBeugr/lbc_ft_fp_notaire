from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit import AuditLog


async def log(
    db: AsyncSession,
    *,
    action: str,
    user_id: str | None = None,
    user_role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    ip: str | None = None,
    detail: dict | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip,
        detail=detail,
    )
    db.add(entry)
    await db.commit()


async def get_logs(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())
