"""
Initialisation — crée les comptes de référence par rôle.
Usage (dans le conteneur api) :
    python seed_admin.py
"""
import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get("DB_URL")
if not DB_URL:
    print("❌ DB_URL non définie.")
    sys.exit(1)

# (email, prénom, nom, rôle, mot_de_passe)
USERS = [
    ("admin@notaire.local",       "Admin",       "Système",      "admin",                   "Admin2026!"),
    ("notaire@notaire.local",     "Maître",      "Dupont",       "notaire_principal",        "Notaire2026!"),
    ("conformite@notaire.local",  "Marie",       "Martin",       "responsable_conformite",   "Conformite2026!"),
    ("clerc@notaire.local",       "Jean",        "Clerc",        "clercs",                   "Clerc2026!"),
]


async def main() -> None:
    import bcrypt

    engine = create_async_engine(DB_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        try:
            await db.execute(text("SELECT 1 FROM users LIMIT 1"))
        except Exception:
            print("❌ Tables introuvables — lancez d'abord : alembic upgrade head")
            await engine.dispose()
            sys.exit(1)

        created, skipped = [], []

        for email, first, last, role, password in USERS:
            r = await db.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})
            if r.fetchone():
                skipped.append(email)
                continue

            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            await db.execute(text("""
                INSERT INTO users (id, email, hashed_password, first_name, last_name,
                                   role, is_active, totp_enabled, must_change_password)
                VALUES (:id, :email, :pwd, :fn, :ln, :role, 1, 0, 0)
            """), {
                "id":    str(uuid.uuid4()),
                "email": email,
                "pwd":   hashed_pw,
                "fn":    first,
                "ln":    last,
                "role":  role,
            })
            created.append((email, role, password))

        await db.commit()

    await engine.dispose()

    print("\n" + "="*65)
    print("✅ COMPTES CRÉÉS")
    print("="*65)
    print(f"  {'Email':<35} {'Mot de passe':<20} Rôle")
    print("-"*65)
    for email, role, password in created:
        print(f"  {email:<35} {password:<20} {role}")

    if skipped:
        print(f"\n⚠️  Déjà existants (ignorés) : {', '.join(skipped)}")

    print("="*65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
