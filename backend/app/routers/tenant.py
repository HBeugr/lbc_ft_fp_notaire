"""Cabinet de la session courante.

Alimente le branding de l'interface (nom du cabinet dans la barre latérale, dans
l'application d'authentification 2FA) et le portier côté client (bandeau de
suspension, quota de sièges atteint).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import branding
from app.core.database import get_db, get_shared_db
from app.core.deps import get_current_user, require_admin, require_user_manager
from app.core.tenant_context import get_current_tenant
from app.models.shared import Tenant
from app.models.user import User
from app.schemas.tenants import (
    LogoContraintesOut,
    LogoOut,
    TenantContextOut,
    TenantMetricsOut,
)

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/me", response_model=TenantContextOut)
async def current_tenant(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_shared_db),
) -> TenantContextOut:
    """Cabinet servant la session — jamais choisi par le client, toujours déduit du jeton."""
    tenant = await db.get(Tenant, get_current_tenant().id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable.")
    return TenantContextOut.model_validate(tenant)


@router.get("/quota", response_model=TenantMetricsOut)
async def tenant_quota(
    _: User = Depends(require_user_manager),
    db: AsyncSession = Depends(get_db),
    shared_db: AsyncSession = Depends(get_shared_db),
) -> TenantMetricsOut:
    """Consommation de sièges du cabinet — consultée avant d'inviter un collaborateur."""
    context = get_current_tenant()
    tenant = await shared_db.get(Tenant, context.id)

    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    actifs = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    ).scalar_one()

    return TenantMetricsOut(
        tenant_id=context.id,
        utilisateurs_actifs=actifs,
        utilisateurs_total=total,
        quota_utilisateurs=tenant.max_users if tenant else 0,
        dossiers_total=0,
    )


# ── Logo du cabinet ──────────────────────────────────────────────────────────

@router.get("/logo/contraintes", response_model=LogoContraintesOut)
async def logo_contraintes(_: User = Depends(get_current_user)) -> LogoContraintesOut:
    """Règles de format, à afficher avant l'envoi plutôt qu'après le refus."""
    return LogoContraintesOut(**branding.contraintes())


@router.get("/logo")
async def get_logo(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_shared_db),
) -> Response:
    """Sert le logo du cabinet courant.

    Le fichier n'est jamais exposé par URL directe de stockage : il transite par
    l'API, qui vérifie que l'appelant appartient bien au cabinet.
    """
    contexte = get_current_tenant()
    tenant = await db.get(Tenant, contexte.id)
    if tenant is None or not tenant.logo_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun logo défini.")

    try:
        contenu = branding.lire_logo(contexte, tenant.logo_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Logo introuvable dans le stockage."
        )

    return Response(
        content=contenu,
        media_type=tenant.logo_content_type or "image/png",
        # Cache court côté navigateur : l'interface ajoute l'horodatage en
        # paramètre, ce qui invalide l'entrée dès que le logo change.
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.put("/logo", response_model=LogoOut)
async def upload_logo(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> LogoOut:
    """Remplace le logo du cabinet — réservé à l'Admin du cabinet.

    Volontairement `require_admin` et non `require_user_manager` : le logo relève
    du paramétrage du cabinet (ADM-07), pas de la gestion des utilisateurs
    (ADM-01). Les deux verrous sont aujourd'hui identiques, mais les adosser
    reviendrait à faire dépendre l'identité visuelle d'une règle de séparation
    des fonctions qui n'a rien à voir — et à l'élargir silencieusement si cette
    règle évoluait.
    """
    contexte = get_current_tenant()
    contenu = await file.read()

    try:
        content_type, extension, largeur, hauteur = branding.valider_logo(
            contenu, file.content_type
        )
    except branding.LogoInvalide as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    cle = branding.enregistrer_logo(contexte, contenu, content_type, extension)

    tenant = await db.get(Tenant, contexte.id)
    tenant.logo_key = cle
    tenant.logo_content_type = content_type
    tenant.logo_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tenant)

    return LogoOut(
        logo_updated_at=tenant.logo_updated_at,
        largeur=largeur, hauteur=hauteur, content_type=content_type,
    )


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_logo(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> None:
    """Retire le logo — l'interface retombe sur le libellé générique. Admin du cabinet."""
    contexte = get_current_tenant()
    tenant = await db.get(Tenant, contexte.id)
    if tenant is None or not tenant.logo_key:
        return
    branding.supprimer_logo(contexte, tenant.logo_key)
    tenant.logo_key = None
    tenant.logo_content_type = None
    tenant.logo_updated_at = None
    await db.commit()
