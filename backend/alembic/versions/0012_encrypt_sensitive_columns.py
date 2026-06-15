"""Chiffrement au repos (AES-256) des colonnes sensibles — CDC §5.2.

Les colonnes PII (n° pièce, n° contribuable, contacts, adresses, RCCM, CNI du BE)
et le narratif libre du DOS sont désormais chiffrés via le type applicatif
EncryptedString (Fernet). On élargit ces colonnes en TEXT pour contenir le
chiffré (préfixe `enc::` + token base64). Les valeurs en clair existantes restent
lisibles (rétro-compatibilité) et seront chiffrées à la prochaine écriture.

Note : les scores et classifications ne sont pas chiffrés (utilisés pour le
filtrage du registre risque élevé et les agrégats) ; les noms restent en clair
(criblage sanctions, tri, affichage).

Révision : 0012
Révision précédente : 0011
"""
from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_PP_COLS = ["adresse_geo", "adresse_postale", "telephone", "whatsapp", "email",
            "numero_piece", "numero_contribuable"]
_PM_COLS = ["nom_representant_legal", "numero_rccm", "numero_contribuable",
            "adresse", "telephone", "whatsapp", "email"]


def upgrade() -> None:
    for col in _PP_COLS:
        op.alter_column("kyc_pp", col, type_=sa.Text(), existing_nullable=True)
    for col in _PM_COLS:
        op.alter_column("kyc_pm", col, type_=sa.Text(), existing_nullable=True)
    op.alter_column("kyc_be", "cni_passeport", type_=sa.Text(), existing_nullable=True)
    # indices_blanchiment et autres_informations (DOS) sont déjà en TEXT.


def downgrade() -> None:
    op.alter_column("kyc_be", "cni_passeport", type_=sa.String(100), existing_nullable=True)
    for col in _PM_COLS:
        length = 255 if col in ("nom_representant_legal", "email") else (500 if col == "adresse" else (30 if col in ("telephone", "whatsapp") else 100))
        op.alter_column("kyc_pm", col, type_=sa.String(length), existing_nullable=True)
    for col in _PP_COLS:
        length = 500 if col == "adresse_geo" else (255 if col in ("adresse_postale", "email") else (30 if col in ("telephone", "whatsapp") else 100))
        op.alter_column("kyc_pp", col, type_=sa.String(length), existing_nullable=True)
