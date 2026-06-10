from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import configure_logging, logger
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
from app.routers import documents as documents_router
from app.routers import rapports as rapports_router
from app.routers import admin as admin_router


def _ensure_minio_bucket() -> None:
    from minio import Minio
    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        if not client.bucket_exists(settings.MINIO_BUCKET_DOCUMENTS):
            client.make_bucket(settings.MINIO_BUCKET_DOCUMENTS)
            logger.info("minio.bucket_created", bucket=settings.MINIO_BUCKET_DOCUMENTS)
    except Exception as exc:
        logger.warning("minio.bucket_init_failed", error=str(exc))


async def _ensure_dos_grants() -> None:
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.engine import URL

    db_name = settings.DB_NAME
    dos_user = settings.DOS_DB_USER
    dos_password = settings.DOS_DB_PASSWORD

    root_url = URL.create(
        drivername="mysql+asyncmy",
        username="root",
        password=settings.DB_ROOT_PASSWORD or settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=db_name,
    )
    statements = [
        f"CREATE USER IF NOT EXISTS '{dos_user}'@'%' IDENTIFIED BY '{dos_password}'",
        f"ALTER USER '{dos_user}'@'%' IDENTIFIED BY '{dos_password}'",
        f"GRANT SELECT, INSERT, UPDATE ON `{db_name}`.`declarations_suspicion` TO '{dos_user}'@'%'",
        f"GRANT SELECT, INSERT ON `{db_name}`.`dos_addendums` TO '{dos_user}'@'%'",
        "FLUSH PRIVILEGES",
    ]
    root_engine = create_async_engine(root_url, pool_size=1, max_overflow=0)
    try:
        async with root_engine.connect() as conn:
            for stmt in statements:
                await conn.execute(sa.text(stmt))
            await conn.commit()
        logger.info("dos.grants_applied", user=dos_user)
    except Exception as exc:
        logger.warning("dos.grants_failed", error=str(exc))
    finally:
        await root_engine.dispose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.APP_ENV)
    logger.info("startup", env=settings.APP_ENV)
    _ensure_minio_bucket()
    await _ensure_dos_grants()
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Notaire LBC/FT/FP — API",
    version="1.0.0",
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

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
app.include_router(documents_router.router, prefix="/api")
app.include_router(rapports_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}
