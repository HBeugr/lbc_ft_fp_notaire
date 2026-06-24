"""Fixtures pytest — suite notaire.

SQLite (aiosqlite) en mémoire (StaticPool → base partagée) ; Redis patché en no-op.
Aucune dépendance à MySQL/Redis/MinIO réels.
"""
import os
import uuid

# Valeurs par défaut requises par la config (avant import de l'app)
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DOS_DB_USER", "test")
os.environ.setdefault("DOS_DB_PASSWORD", "test")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("JWT_SECRET", "test_secret_at_least_32_characters_ok!")
os.environ.setdefault("AES_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGU=")
os.environ.setdefault("TOTP_REQUIRED", "true")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from app.core.database import Base, get_db, get_dos_db
from app.core import security
# Import des modèles pour enregistrer les tables sur Base.metadata
import app.models.user  # noqa: F401
import app.models.alerte  # noqa: F401
import app.models.dossier  # noqa: F401
import app.models.audit  # noqa: F401
import app.models.dos  # noqa: F401
import app.models.revision  # noqa: F401
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_dos_db] = override_get_db

    fake_redis = AsyncMock(
        get=AsyncMock(return_value=None),
        set=AsyncMock(), setex=AsyncMock(), delete=AsyncMock(),
        incr=AsyncMock(return_value=1), expire=AsyncMock(),
    )
    with patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=fake_redis)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Helpers de seed ───────────────────────────────────────────────────────────

async def create_user(db: AsyncSession, role: str = "responsable_conformite", **kwargs):
    from app.models.user import User
    defaults = dict(
        id=str(uuid.uuid4()),
        email=f"u_{uuid.uuid4().hex[:8]}@test.ci",
        hashed_password=security.hash_password("TestPass123!"),
        first_name="Test", last_name="User",
        role=role, is_active=True, totp_enabled=False, must_change_password=False,
    )
    user = User(**{**defaults, **kwargs})
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_dossier(db: AsyncSession, created_by: str, **kwargs):
    from app.models.dossier import Dossier
    defaults = dict(
        id=str(uuid.uuid4()),
        reference=f"KYC-{uuid.uuid4().hex[:8].upper()}",
        type_client="PP", type_operation="vente_immobiliere",
        statut="en_analyse", created_by=created_by, assigned_to=None,
    )
    dossier = Dossier(**{**defaults, **kwargs})
    db.add(dossier)
    await db.commit()
    await db.refresh(dossier)
    return dossier


async def create_alerte(db: AsyncSession, **kwargs):
    from app.models.alerte import Alerte
    defaults = dict(
        id=str(uuid.uuid4()), dossier_id=None,
        type_alerte="INCOHERENCE_DOC", niveau="MOYEN", statut="ouverte",
        description="Alerte de test",
    )
    alerte = Alerte(**{**defaults, **kwargs})
    db.add(alerte)
    await db.commit()
    await db.refresh(alerte)
    return alerte


def auth_headers(user) -> dict:
    token = security.create_access_token(user.id, extra={"role": user.role, "totp_pending": False})
    return {"Authorization": f"Bearer {token}"}
