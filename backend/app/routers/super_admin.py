"""Console d'exploitation de la plateforme — Super-Admin.

Ce router administre des **cabinets**, jamais leurs données. C'est la
traduction technique d'une exigence de conformité : l'exploitant de la
plateforme héberge des dossiers LBC/FT sans pouvoir les consulter (Art. 63,
confidentialité CENTIF).

L'étanchéité repose sur trois choix cumulés, pas sur la seule interface :

1. Les comptes Super-Admin vivent dans `shared.super_admins` et n'existent dans
   aucun schéma cabinet — ils ne peuvent donc pas obtenir de session métier.
2. Leurs jetons portent `scope=platform` et **aucun** claim `tid` ; le
   middleware refuse toute requête métier sans cabinet identifié.
3. Les endpoints ci-dessous n'ouvrent que des sessions `shared`, à deux
   exceptions explicites et bornées : le comptage de volumétrie et les
   migrations, qui ne lisent aucun contenu.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import branding, security
from app.core.database import get_shared_db, tenant_session
from app.core.logging import logger
from app.core.redis_client import get_login_attempts, increment_login_attempts, reset_login_attempts
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.shared import SuperAdmin, Tenant, TenantAuditLog
from app.models.dossier import Dossier
from app.models.user import User
from app.schemas.tenants import (
    LogoContraintesOut,
    LogoOut,
    MigrationResultOut,
    SuperAdminLoginRequest,
    SuperAdminLoginResponse,
    SuperAdminOut,
    SuperAdminPasswordChangeRequest,
    TenantCreateRequest,
    TenantCreateResponse,
    TenantMetricsOut,
    TenantOut,
    TenantStatutRequest,
)
from app.services import tenant_provisioning
from app.services.tenant_provisioning import ProvisioningError

router = APIRouter(prefix="/super-admin", tags=["super-admin"])

# Endpoint de jeton distinct de celui des cabinets : les deux populations
# n'ont ni le même magasin de comptes ni la même portée.
oauth2_platform = OAuth2PasswordBearer(tokenUrl="/api/super-admin/auth/login")

_PLATFORM_SCOPE = "platform"
_MAX_LOGIN_ATTEMPTS = 5


# ── Authentification ─────────────────────────────────────────────────────────

async def get_current_super_admin(
    token: str = Depends(oauth2_platform),
    db: AsyncSession = Depends(get_shared_db),
) -> SuperAdmin:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.decode_token(token)
    except Exception:
        raise credentials_exc

    # Un jeton de cabinet ne doit jamais ouvrir la console d'exploitation, et
    # réciproquement : la portée est vérifiée explicitement.
    if payload.get("type") != "access" or payload.get("scope") != _PLATFORM_SCOPE:
        raise credentials_exc

    admin = await db.get(SuperAdmin, payload.get("sub") or "")
    if admin is None or not admin.is_active:
        raise credentials_exc
    return admin


@router.post("/auth/login", response_model=SuperAdminLoginResponse)
async def super_admin_login(
    body: SuperAdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_shared_db),
) -> SuperAdminLoginResponse:
    ip = request.client.host if request.client else "unknown"
    if await get_login_attempts(ip, body.email) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez dans 15 minutes.",
        )

    admin = (
        await db.execute(select(SuperAdmin).where(SuperAdmin.email == body.email.strip().lower()))
    ).scalar_one_or_none()

    if admin is None or not security.verify_password(body.password, admin.hashed_password):
        await increment_login_attempts(ip, body.email)
        logger.warning("super_admin.login_failed", email=body.email, ip=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect."
        )
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé.")

    await reset_login_attempts(ip, body.email)
    token = security.create_access_token(admin.id, extra={"scope": _PLATFORM_SCOPE})
    return SuperAdminLoginResponse(
        access_token=token, super_admin=SuperAdminOut.model_validate(admin)
    )


@router.get("/auth/me", response_model=SuperAdminOut)
async def super_admin_me(admin: SuperAdmin = Depends(get_current_super_admin)) -> SuperAdminOut:
    return SuperAdminOut.model_validate(admin)


@router.patch("/auth/password", response_model=SuperAdminOut)
async def super_admin_change_password(
    body: SuperAdminPasswordChangeRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> SuperAdminOut:
    if not security.verify_password(body.current_password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect."
        )
    stored = await db.get(SuperAdmin, admin.id)
    stored.hashed_password = security.hash_password(body.new_password)
    stored.must_change_password = False
    await db.commit()
    await db.refresh(stored)
    return SuperAdminOut.model_validate(stored)


# ── Gestion des cabinets ─────────────────────────────────────────────────────

@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> list[TenantOut]:
    rows = (await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))).scalars().all()
    return [TenantOut.model_validate(t) for t in rows]


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: str,
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> TenantOut:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable.")
    return TenantOut.model_validate(tenant)


@router.post("/tenants", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreateRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
) -> TenantCreateResponse:
    """Provisionne un cabinet : schéma, migrations, clé, stockage, compte admin."""
    try:
        result = await tenant_provisioning.provision_tenant(
            nom_cabinet=body.nom_cabinet,
            contact_email=body.contact_email,
            admin_email=body.admin_email,
            admin_first_name=body.admin_first_name,
            admin_last_name=body.admin_last_name,
            slug=body.slug,
            numero_agrement=body.numero_agrement,
            pays=body.pays,
            contact_telephone=body.contact_telephone,
            adresse=body.adresse,
            totp_required=body.totp_required,
            max_users=body.max_users,
            super_admin_id=admin.id,
        )
    except ProvisioningError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return TenantCreateResponse(
        tenant=TenantOut.model_validate(result.tenant),
        admin_email=result.admin_email,
        admin_temp_password=result.admin_temp_password,
    )


async def _set_statut(tenant_id: str, statut: str, motif: str | None, admin_id: str) -> TenantOut:
    try:
        tenant = await tenant_provisioning.set_tenant_statut(
            tenant_id, statut, motif=motif, super_admin_id=admin_id
        )
    except ProvisioningError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return TenantOut.model_validate(tenant)


@router.post("/tenants/{tenant_id}/activate", response_model=TenantOut)
async def activate_tenant(
    tenant_id: str, admin: SuperAdmin = Depends(get_current_super_admin)
) -> TenantOut:
    """Met le cabinet en production — ses utilisateurs peuvent se connecter."""
    return await _set_statut(tenant_id, "production", None, admin.id)


@router.post("/tenants/{tenant_id}/suspend", response_model=TenantOut)
async def suspend_tenant(
    tenant_id: str,
    body: TenantStatutRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
) -> TenantOut:
    """Coupe l'accès sans toucher aux données (conservation Art. 23 préservée)."""
    return await _set_statut(tenant_id, "suspendu", body.motif, admin.id)


@router.post("/tenants/{tenant_id}/archive", response_model=TenantOut)
async def archive_tenant(
    tenant_id: str,
    body: TenantStatutRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
) -> TenantOut:
    """Archive le cabinet.

    Le schéma et ses données sont **conservés** : la suppression physique reste
    interdite avant 10 ans (Art. 23, Art. 197). L'archivage ne fait que fermer
    définitivement l'accès applicatif.
    """
    return await _set_statut(tenant_id, "archive", body.motif, admin.id)


@router.get("/tenants/{tenant_id}/metrics", response_model=TenantMetricsOut)
async def tenant_metrics(
    tenant_id: str,
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> TenantMetricsOut:
    """Volumétrie d'un cabinet — pour le dimensionnement et les quotas.

    Seuls des `COUNT(*)` sont exécutés : aucun contenu de dossier n'est lu ni
    retourné. C'est la limite exacte de ce que l'exploitant peut voir.
    """
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable.")

    context = TenantContext(
        id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
        statut=tenant.statut, key_salt=tenant.key_salt, totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )
    with tenant_scope(context):
        async with tenant_session(context) as tdb:
            total = (await tdb.execute(select(func.count()).select_from(User))).scalar_one()
            actifs = (
                await tdb.execute(
                    select(func.count()).select_from(User).where(User.is_active.is_(True))
                )
            ).scalar_one()
            dossiers = (await tdb.execute(select(func.count()).select_from(Dossier))).scalar_one()

    return TenantMetricsOut(
        tenant_id=tenant_id,
        utilisateurs_actifs=actifs,
        utilisateurs_total=total,
        quota_utilisateurs=tenant.max_users,
        dossiers_total=dossiers,
    )


@router.post("/tenants/migrate", response_model=MigrationResultOut)
async def migrate_tenants(
    admin: SuperAdmin = Depends(get_current_super_admin),
) -> MigrationResultOut:
    """Rejoue les migrations métier sur tous les cabinets.

    En schéma-par-tenant, `alembic upgrade head` ne suffit plus au déploiement :
    chaque schéma porte sa propre table de versions. Cet endpoint boucle sur
    l'annuaire et remonte le résultat cabinet par cabinet — un échec isolé
    n'interrompt pas les autres.
    """
    results = await tenant_provisioning.migrate_all_tenants()
    logger.info("tenants.migrated", super_admin_id=admin.id, results=results)
    return MigrationResultOut(resultats=results)


@router.get("/audit", response_model=list[dict])
async def exploitation_audit(
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
    limit: int = 100,
) -> list[dict]:
    """Journal d'exploitation — distinct de l'audit métier, qui reste dans les cabinets."""
    rows = (
        await db.execute(
            select(TenantAuditLog).order_by(TenantAuditLog.created_at.desc()).limit(min(limit, 500))
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "super_admin_id": r.super_admin_id,
            "action": r.action,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ── Logo d'un cabinet (exploitation) ─────────────────────────────────────────
#
# Le Super-Admin peut poser ou remplacer le logo d'un cabinet — typiquement à la
# création, quand le cabinet n'a encore aucun utilisateur pour le faire lui-même.
# C'est une donnée d'identité visuelle, pas une donnée métier : y toucher ne
# rompt pas l'aveuglement de l'exploitant aux dossiers.


def _contexte_de(tenant: Tenant) -> TenantContext:
    return TenantContext(
        id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
        statut=tenant.statut, key_salt=tenant.key_salt, totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )


@router.get("/logo/contraintes", response_model=LogoContraintesOut)
async def super_admin_logo_contraintes(
    _: SuperAdmin = Depends(get_current_super_admin),
) -> LogoContraintesOut:
    return LogoContraintesOut(**branding.contraintes())


@router.get("/tenants/{tenant_id}/logo")
async def super_admin_get_logo(
    tenant_id: str,
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> Response:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not tenant.logo_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun logo défini.")
    contexte = _contexte_de(tenant)
    try:
        contenu = branding.lire_logo(contexte, tenant.logo_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Logo introuvable dans le stockage."
        )
    return Response(
        content=contenu,
        media_type=tenant.logo_content_type or "image/png",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.put("/tenants/{tenant_id}/logo", response_model=LogoOut)
async def super_admin_upload_logo(
    tenant_id: str,
    file: UploadFile = File(...),
    admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> LogoOut:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cabinet introuvable.")

    contenu = await file.read()
    try:
        content_type, extension, largeur, hauteur = branding.valider_logo(
            contenu, file.content_type
        )
    except branding.LogoInvalide as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    contexte = _contexte_de(tenant)
    tenant.logo_key = branding.enregistrer_logo(contexte, contenu, content_type, extension)
    tenant.logo_content_type = content_type
    tenant.logo_updated_at = datetime.now(timezone.utc)
    db.add(TenantAuditLog(
        tenant_id=tenant_id, super_admin_id=admin.id, action="tenant.logo.updated",
        detail=f"{largeur}×{hauteur} px, {content_type}",
    ))
    await db.commit()
    await db.refresh(tenant)

    return LogoOut(
        logo_updated_at=tenant.logo_updated_at,
        largeur=largeur, hauteur=hauteur, content_type=content_type,
    )


# `response_model=None` est explicite à dessein : ce module active
# `from __future__ import annotations`, donc l'annotation `-> None` arrive à
# FastAPI sous forme de chaîne, qu'il résout en `NoneType` et prend alors pour un
# modèle de réponse — incompatible avec un 204, qui interdit tout corps.
@router.delete(
    "/tenants/{tenant_id}/logo",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def super_admin_delete_logo(
    tenant_id: str,
    admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> None:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not tenant.logo_key:
        return
    branding.supprimer_logo(_contexte_de(tenant), tenant.logo_key)
    tenant.logo_key = None
    tenant.logo_content_type = None
    tenant.logo_updated_at = None
    db.add(TenantAuditLog(
        tenant_id=tenant_id, super_admin_id=admin.id, action="tenant.logo.removed",
    ))
    await db.commit()
