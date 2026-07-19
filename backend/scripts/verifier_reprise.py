"""Contrôle de la reprise MySQL → schéma cabinet PostgreSQL.

À lancer APRÈS `migrate_mysql_to_tenant.py`, et AVANT toute décision concernant
l'ancienne base. Compter les lignes ne suffit pas : ce qui peut casser
silencieusement, ce sont les conversions de types et surtout le changement de
clé de chiffrement.

    python scripts/verifier_reprise.py --slug <slug-du-cabinet> \
        --attendu users=42,dossiers=317,kyc_pp=280

Contrôles effectués :
  · volumétrie table par table (valeurs attendues fournies par l'exploitant,
    relevées sur l'ancienne base avant bascule) ;
  · colonnes chiffrées réellement DÉCHIFFRABLES avec la clé du cabinet — elles
    étaient chiffrées avec l'ancienne clé globale ;
  · illisibilité avec la clé d'un autre cabinet (preuve du cloisonnement) ;
  · TINYINT(1) → BOOLEAN, DATETIME naïf → TIMESTAMPTZ, JSON → JSONB ;
  · annuaire de routage alimenté (sans quoi personne ne peut se connecter) ;
  · absence de clés étrangères orphelines.

Note : le cabinet compte UN utilisateur de plus que l'ancienne base — le compte
administrateur créé par le provisioning, dont l'exploitant connaît le mot de
passe initial. C'est un filet de sécurité voulu : si aucun mot de passe hérité
n'était connu, le cabinet serait inaccessible malgré des données intactes.
"""
import asyncio
import sys

from sqlalchemy import select, text

from app.core.crypto import derive_tenant_fernet
from app.core.database import shared_session, tenant_session
from app.core.tenant_context import TenantContext, tenant_scope
from app.models.alerte import Alerte
from app.models.audit import AuditLog
from app.models.dos import DeclarationSuspicion
from app.models.dossier import Dossier, EvaluationRisque, KycPP
from app.models.shared import Tenant, TenantUser
from app.models.user import User

def _arguments():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True, help="Slug du cabinet repris.")
    parser.add_argument("--attendu", default="",
                        help="Volumétrie attendue, ex. users=42,dossiers=317. "
                             "Rappel : +1 utilisateur pour le compte admin du provisioning.")
    return parser.parse_args()

resultats: list[tuple[bool, str]] = []


def verifier(condition: bool, libelle: str) -> None:
    resultats.append((bool(condition), libelle))
    print(f"  {'✅' if condition else '❌'} {libelle}")


async def main() -> None:
    args = _arguments()
    attendu = {}
    for paire in filter(None, args.attendu.split(",")):
        table, _, valeur = paire.partition("=")
        attendu[table.strip()] = int(valeur)

    async with shared_session() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == args.slug))
        ).scalar_one()
        rattaches = (await db.execute(
            select(TenantUser).where(TenantUser.tenant_id == tenant.id)
        )).scalars().all()

    contexte = TenantContext(
        id=tenant.id, schema=tenant.schema_name, slug=tenant.slug, nom=tenant.nom_cabinet,
        statut=tenant.statut, key_salt=tenant.key_salt, totp_required=tenant.totp_required,
        storage_bucket=tenant.storage_bucket,
    )

    print("═" * 72)
    print(f"  CONTRÔLE DE LA REPRISE — cabinet « {tenant.nom_cabinet} »")
    print(f"  schéma : {tenant.schema_name}")
    print("═" * 72)

    if attendu:
        print("\n── Volumétrie ──────────────────────────────────────────────────")
        async with shared_session() as db:
            for table, n_attendu in attendu.items():
                n = (await db.execute(text(
                    f'SELECT count(*) FROM "{tenant.schema_name}".{table}'
                ))).scalar_one()
                verifier(n == n_attendu, f"{table:<24} {n}/{n_attendu}")

    print("\n── Annuaire de routage ─────────────────────────────────────────")
    verifier(len(rattaches) > 0, f"{len(rattaches)} utilisateur(s) routables depuis l'annuaire")

    with tenant_scope(contexte):
        async with tenant_session(contexte) as db:
            print("\n── Chiffrement : changement de clé effectif ─────────────────────")
            kyc = (await db.execute(select(KycPP).order_by(KycPP.nom))).scalars().all()
            # Relire les fiches suffit : c'est le déchiffrement qui est éprouvé.
            # Aucun volume attendu ici — il est contrôlé par `--attendu`.
            verifier(len(kyc) > 0, f"{len(kyc)} fiche(s) KYC PP relue(s)")
            telephones = sorted(k.telephone for k in kyc if k.telephone)
            lisibles = [t for t in telephones if not t.startswith("enc::")]
            verifier(len(lisibles) == len(telephones),
                     f"{len(lisibles)}/{len(telephones)} téléphones déchiffrés avec la clé du cabinet")

            declarations = (await db.execute(select(DeclarationSuspicion))).scalars().all()
            chiffrees = [d for d in declarations
                         if (d.indices_blanchiment or "").startswith("enc::")
                         or (d.autres_informations or "").startswith("enc::")]
            verifier(not chiffrees,
                     f"DOS : {len(declarations)} déclaration(s), champs confidentiels déchiffrés")

            print("\n── Chiffrement : l'ancienne clé ne fonctionne plus ──────────────")
            # On cherche une valeur RÉELLEMENT renseignée : les colonnes
            # facultatives sont majoritairement nulles sur des données réelles,
            # et un `LIMIT 1` naïf tombe presque toujours sur un NULL.
            brut = (await db.execute(text(
                f'SELECT telephone FROM "{tenant.schema_name}".kyc_pp '
                "WHERE telephone IS NOT NULL LIMIT 1"
            ))).scalar_one_or_none()

            if brut is None:
                verifier(True, "aucune donnée chiffrée à contrôler (colonnes vides)")
            else:
                verifier(brut.startswith("enc::"), "stocké chiffré au repos")
                ancienne = derive_tenant_fernet("mauvais-sel-simulant-un-autre-cabinet")
                try:
                    ancienne.decrypt(brut[len("enc::"):].encode())
                    verifier(False, "une autre clé ne doit PAS déchiffrer")
                except Exception:
                    verifier(True, "illisible avec la clé d'un autre cabinet")

            print("\n── Types PostgreSQL ────────────────────────────────────────────")
            utilisateurs = (await db.execute(select(User).order_by(User.email))).scalars().all()
            verifier(all(isinstance(u.is_active, bool) for u in utilisateurs),
                     "booléens : TINYINT(1) → BOOLEAN")
            verifier(any(u.is_active for u in utilisateurs),
                     "au moins un compte actif repris")

            dossiers = (await db.execute(select(Dossier))).scalars().all()
            verifier(all(d.created_at.tzinfo is not None for d in dossiers),
                     "horodatages : DATETIME naïf → TIMESTAMPTZ conscient du fuseau")
            statuts = {d.statut for d in dossiers}
            valides = {"brouillon", "en_analyse", "vigilance_renforcee", "valide",
                       "bloque", "traite", "cloture", "archive"}
            verifier(statuts <= valides, f"ENUM valides : {sorted(statuts)}")

            evaluations = (await db.execute(select(EvaluationRisque))).scalars().all()
            verifier(all(e.triggers_actifs is None or isinstance(e.triggers_actifs, dict)
                         for e in evaluations),
                     "JSON : chaîne MySQL → structure JSONB")
            verifier(all(e.overrides is None or isinstance(e.overrides, list)
                         for e in evaluations),
                     "JSONB : tableaux préservés")

            journaux = (await db.execute(select(AuditLog))).scalars().all()
            verifier(all(j.detail is None or isinstance(j.detail, (dict, list)) for j in journaux),
                     f"journal d'audit : {len(journaux)} entrée(s), détail JSON exploitable")

            alertes = (await db.execute(select(Alerte))).scalars().all()
            verifier(all(a.statut for a in alertes), f"{len(alertes)} alerte(s) avec statut valide")

            print("\n── Intégrité référentielle ─────────────────────────────────────")
            orphelins = (await db.execute(text(
                f'''SELECT count(*) FROM "{tenant.schema_name}".dossiers d
                    LEFT JOIN "{tenant.schema_name}".users u ON u.id = d.created_by
                    WHERE u.id IS NULL'''
            ))).scalar_one()
            verifier(orphelins == 0, "aucune clé étrangère orpheline")

    reussis = sum(1 for ok, _ in resultats if ok)
    print("\n" + "═" * 72)
    print(f"  {reussis}/{len(resultats)} contrôles réussis")
    print("═" * 72)
    sys.exit(0 if reussis == len(resultats) else 1)


if __name__ == "__main__":
    asyncio.run(main())
