from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.core import dos_privileges
from app.core.tenant_context import NoTenantContextError
from app.core.tenant_middleware import TenantMiddleware
from app.routers import auth as auth_router
from app.routers import totp as totp_router
from app.routers import users as users_router
from app.routers import audit as audit_router
from app.routers import dossiers as dossiers_router
from app.routers import kyc as kyc_router
from app.routers import alertes as alertes_router
from app.routers import dos as dos_router
from app.routers import revisions as revisions_router
from app.routers import registres as registres_router
from app.routers import scoring as scoring_router
from app.routers import sanctions as sanctions_router
from app.routers import kyc_screening as kyc_screening_router
from app.routers import documents as documents_router
from app.routers import rapports as rapports_router
from app.routers import admin as admin_router
from app.routers import dashboard as dashboard_router
from app.routers import procedures as procedures_router
from app.routers import autorisations as autorisations_router
from app.routers import super_admin as super_admin_router
from app.routers import tenant as tenant_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.APP_ENV)
    logger.info("startup", env=settings.APP_ENV)
    # Échec au démarrage plutôt qu'à la première écriture : une clé maîtresse
    # absente en production arme une bombe à retardement (cf. `crypto._master_key`).
    from app.core.crypto import MasterKeyManquante, _master_key

    try:
        _master_key()
    except MasterKeyManquante as exc:
        logger.error("startup.master_key_manquante", detail=str(exc))
        raise
    # Les privilèges DOS sont posés dans chaque schéma cabinet (Art. 63) ; les
    # cabinets créés ensuite les reçoivent à leur provisioning.
    await dos_privileges.apply_to_all_tenants()
    # La configuration de scoring n'est plus chargée au démarrage : elle est
    # propre à chaque cabinet et serait donc fausse pour tous sauf un. Elle est
    # désormais chargée paresseusement, à la première requête de chaque cabinet
    # (cf. `runtime_config.ensure_loaded`).
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Notaire LBC/FT/FP — API",
    version="1.0.0",
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.exception_handler(NoTenantContextError)
async def _no_tenant_context(request: Request, exc: NoTenantContextError) -> JSONResponse:
    """Requête métier sans cabinet identifié → 401, jamais 500.

    Le cas nominal est une requête sans jeton (ou avec un jeton illisible) sur un
    endpoint protégé : FastAPI peut résoudre `Depends(get_db)` avant
    `Depends(get_current_user)`, si bien que l'absence de cabinet se manifeste
    avant que le contrôle d'authentification n'ait eu lieu.

    Sans ce gestionnaire, l'API renverrait une 500 — bruit inutile en supervision,
    et fuite d'information sur la pile interne.
    """
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Authentification requise."},
        headers={"WWW-Authenticate": "Bearer"},
    )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """En-têtes de sécurité au niveau application (défense en profondeur, même hors nginx)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cache-Control", "no-store")
        # API JSON only — CSP verrouillée (aucune ressource active servie par l'API)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        # HSTS uniquement hors dev (évite d'épingler du HTTP en local)
        if settings.APP_ENV != "development":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
            )
        return response


# Starlette exécute les middlewares dans l'ordre INVERSE de leur ajout : le
# dernier ajouté est le plus externe. L'ordre ci-dessous donne donc, de
# l'extérieur vers l'intérieur : CORS → Tenant → SecurityHeaders → routes.
#
# CORS doit rester le plus externe : `TenantMiddleware` répond lui-même 401/402
# (cabinet inconnu, cabinet suspendu), et sans en-têtes CORS le navigateur
# masquerait ces réponses au frontend, qui ne pourrait pas afficher le message
# de suspension.
#
# `TenantMiddleware` doit rester au-dessus des routes : le cabinet doit être
# résolu avant que FastAPI ne résolve les dépendances de l'endpoint, `get_db`
# en particulier.
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(TenantMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api")
app.include_router(totp_router.router, prefix="/api")
app.include_router(users_router.router, prefix="/api")
app.include_router(audit_router.router, prefix="/api")
app.include_router(dossiers_router.router, prefix="/api")
app.include_router(kyc_router.router, prefix="/api")
app.include_router(alertes_router.router, prefix="/api")
app.include_router(dos_router.router, prefix="/api")
app.include_router(revisions_router.router, prefix="/api")
app.include_router(registres_router.router, prefix="/api")
app.include_router(scoring_router.router, prefix="/api")
app.include_router(scoring_router.sim_router, prefix="/api")
app.include_router(sanctions_router.router, prefix="/api")
app.include_router(kyc_screening_router.router, prefix="/api")
app.include_router(documents_router.router, prefix="/api")
app.include_router(rapports_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")
app.include_router(dashboard_router.router, prefix="/api")
app.include_router(procedures_router.router, prefix="/api")
app.include_router(autorisations_router.router, prefix="/api")
app.include_router(tenant_router.router, prefix="/api")
# Console d'exploitation — n'ouvre que des sessions sur l'annuaire `shared`.
app.include_router(super_admin_router.router, prefix="/api")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}
