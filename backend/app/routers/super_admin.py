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
from app.core.config import settings
from app.core.database import get_shared_db, tenant_session
from app.core.logging import logger
from app.core.redis_client import (
    get_login_attempts,
    increment_login_attempts,
    is_token_revoked,
    reset_login_attempts,
    revoke_token,
)
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.shared import SuperAdmin, Tenant, TenantAuditLog
from app.models.dossier import Dossier
from app.models.user import User
from app.schemas.tenants import (
    LogoContraintesOut,
    LogoOut,
    MigrationResultOut,
    PlatformMetricsOut,
    SuperAdminLoginRequest,
    SuperAdminLoginResponse,
    SuperAdminOut,
    SuperAdminPasswordChangeRequest,
    TenantAdminResetResponse,
    TenantCreateRequest,
    TenantCreateResponse,
    TenantMetricsOut,
    TenantOut,
    TenantStatutRequest,
    TenantUpdateRequest,
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

async def _resolve_super_admin(token: str, db: AsyncSession) -> SuperAdmin:
    """Valide un jeton de portée `platform` et retourne son porteur."""
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

    # Déconnexion explicite : le jeton est dans la liste de révocation jusqu'à
    # sa date d'expiration. Sans ce contrôle, « se déconnecter » ne serait
    # qu'un effacement côté navigateur.
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise credentials_exc

    admin = await db.get(SuperAdmin, payload.get("sub") or "")
    if admin is None or not admin.is_active:
        raise credentials_exc
    return admin


async def get_current_super_admin(
    token: str = Depends(oauth2_platform),
    db: AsyncSession = Depends(get_shared_db),
) -> SuperAdmin:
    return await _resolve_super_admin(token, db)


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


# `response_model=None` est indispensable ici, contrairement au logout cabinet :
# ce module active `from __future__ import annotations`, donc `-> None` arrive à
# FastAPI sous forme de chaîne, qu'il résout en la classe `NoneType`. Cette
# classe est « truthy », FastAPI en déduit un corps de réponse et refuse le 204.
@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def super_admin_logout(token: str = Depends(oauth2_platform)) -> None:
    """Révoque le jeton courant côté serveur.

    Sans révocation, un jeton exfiltré resterait valide jusqu'à son expiration
    quoi que fasse l'utilisateur : la déconnexion ne serait qu'un `clear()` de
    session côté navigateur. Le TTL de révocation est calé sur la durée de vie
    du jeton — au-delà, l'entrée n'a plus d'utilité.

    Aucune authentification n'est exigée au-delà du jeton lui-même : présenter
    un jeton déjà révoqué ou expiré doit rester un succès silencieux, sinon la
    déconnexion échouerait précisément dans le cas où elle n'a plus d'objet.
    """
    jti = security.token_jti(token)
    if jti:
        await revoke_token(jti, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)


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
    logger.info("super_admin.password_changed", super_admin_id=admin.id)
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


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
) -> TenantOut:
    """Corrige les attributs administratifs d'un cabinet après sa création.

    Sans cet endpoint, une faute de frappe sur le nom ou une erreur de quota
    était définitive : seul le logo pouvait être repris.
    """
    # `exclude_unset` et non `exclude_none` : à défaut, un champ volontairement
    # remis à vide (téléphone, adresse, agrément) serait silencieusement ignoré.
    changes = body.model_dump(exclude_unset=True)
    try:
        tenant = await tenant_provisioning.update_tenant(
            tenant_id, changes, super_admin_id=admin.id
        )
    except ProvisioningError as exc:
        message = str(exc)
        code = (
            status.HTTP_404_NOT_FOUND
            if "introuvable" in message
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=message)
    return TenantOut.model_validate(tenant)


@router.post("/tenants/{tenant_id}/admin-password-reset", response_model=TenantAdminResetResponse)
async def reset_tenant_admin_password(
    tenant_id: str,
    admin: SuperAdmin = Depends(get_current_super_admin),
) -> TenantAdminResetResponse:
    """Rétablit l'accès d'un cabinet dont le mot de passe admin est perdu.

    Borné au compte de rôle `admin` du cabinet : l'exploitant rouvre la porte
    d'entrée, il ne prend pas la main sur les comptes métier. La 2FA de ce
    compte est également réinitialisée — cf. `reset_tenant_admin_password`.
    """
    try:
        email, temp_password = await tenant_provisioning.reset_tenant_admin_password(
            tenant_id, super_admin_id=admin.id
        )
    except ProvisioningError as exc:
        message = str(exc)
        code = (
            status.HTTP_404_NOT_FOUND
            if "introuvable" in message
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=message)
    return TenantAdminResetResponse(admin_email=email, admin_temp_password=temp_password)


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


@router.get("/metrics", response_model=PlatformMetricsOut)
async def platform_metrics(
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_shared_db),
) -> PlatformMetricsOut:
    """Agrégat plateforme — page d'accueil de la console.

    Le comptage parcourt un schéma après l'autre : il n'existe pas de vue
    globale en schéma-par-tenant, et c'est précisément l'isolation recherchée.
    Le coût est linéaire en nombre de cabinets ; à l'échelle d'une chambre
    notariale nationale, cela reste quelques dizaines de `COUNT(*)`. Si le parc
    grandissait, le calcul devrait passer en tâche planifiée plutôt qu'être
    servi à chaud.

    Un cabinet dont le comptage échoue (migration en cours, schéma indisponible)
    est listé dans `cabinets_injoignables` au lieu de faire échouer la page :
    la console doit rester utilisable pour réparer précisément ce cabinet-là.
    """
    tenants = (
        await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    ).scalars().all()

    par_statut: dict[str, int] = {}
    for tenant in tenants:
        par_statut[tenant.statut] = par_statut.get(tenant.statut, 0) + 1

    utilisateurs_total = 0
    utilisateurs_actifs = 0
    dossiers_total = 0
    injoignables: list[str] = []

    for tenant in tenants:
        # Un cabinet en `configuration` peut ne pas avoir de schéma exploitable ;
        # un cabinet archivé n'a plus d'activité à comptabiliser.
        if tenant.statut == "archive":
            continue
        context = TenantContext(
            id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
            statut=tenant.statut, key_salt=tenant.key_salt, totp_required=tenant.totp_required,
            storage_bucket=tenant.storage_bucket,
        )
        try:
            with tenant_scope(context):
                async with tenant_session(context) as tdb:
                    utilisateurs_total += (
                        await tdb.execute(select(func.count()).select_from(User))
                    ).scalar_one()
                    utilisateurs_actifs += (
                        await tdb.execute(
                            select(func.count()).select_from(User).where(User.is_active.is_(True))
                        )
                    ).scalar_one()
                    dossiers_total += (
                        await tdb.execute(select(func.count()).select_from(Dossier))
                    ).scalar_one()
        except Exception:
            logger.warning("platform_metrics.tenant_unreachable", tenant_id=tenant.id)
            injoignables.append(tenant.nom_cabinet)

    return PlatformMetricsOut(
        cabinets_total=len(tenants),
        cabinets_par_statut=par_statut,
        utilisateurs_total=utilisateurs_total,
        utilisateurs_actifs=utilisateurs_actifs,
        dossiers_total=dossiers_total,
        cabinets_injoignables=injoignables,
        cabinets_recents=[TenantOut.model_validate(t) for t in tenants[:5]],
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
