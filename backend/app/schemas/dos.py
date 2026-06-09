from pydantic import BaseModel
from typing import Literal


class MotifsCentifSchema(BaseModel):
    model_config = {"extra": "allow"}
    operations_insolites: bool = False
    montants_incoherents: bool = False
    identite_douteuse: bool = False
    refus_informations: bool = False
    transactions_fractionnees: bool = False
    intermediaires_inconnus: bool = False
    pays_risque: bool = False
    structure_opaque: bool = False
    fonds_origine_inconnue: bool = False
    comportement_suspect: bool = False
    declarations_contradictoires: bool = False
    pression_notable: bool = False
    urgence_injustifiee: bool = False
    autre: str = ""


class StatutOperationsSchema(BaseModel):
    model_config = {"extra": "allow"}
    operation_realisee: bool = False
    operation_en_cours: bool = False
    operation_non_realisee: bool = False
    date_operation: str | None = None
    motif_non_realisation: str = ""
    statut: str = ""
    montant_fcfa: float | None = None
    description: str = ""


class TransactionSchema(BaseModel):
    model_config = {"extra": "allow"}
    montant: float | None = None
    devise: str = "FCFA"
    mode_paiement: str = ""
    date_transaction: str | None = None
    date: str | None = None
    description: str = ""


class SupportSchema(BaseModel):
    model_config = {"extra": "allow"}
    virement_bancaire: bool = False
    especes: bool = False
    cheque: bool = False
    cryptomonnaie: bool = False
    mobile_money: bool = False
    titres_valeurs: bool = False
    immobilier: bool = False
    societe_ecran: bool = False
    fiducie: bool = False
    assurance_vie: bool = False
    autre: str = ""
    autre_detail: str = ""


class DosCreate(BaseModel):
    dossier_id: str


class DosUpsert(BaseModel):
    # Section 1 — Organisme déclarant
    organisme_libelle: str | None = None
    organisme_adresse: str | None = None
    organisme_email: str | None = None
    organisme_telephone: str | None = None
    # Section 3 — Type de soupçon
    type_soupcon_bc: bool = False
    type_soupcon_ft: bool = False
    type_soupcon_prolif: bool = False
    motifs: MotifsCentifSchema | None = None
    # Section 4 — Statut opérations
    statut_operations: StatutOperationsSchema | None = None
    # Section 5 — Transactions
    detail_transactions: list[TransactionSchema] | None = None
    # Section 6 — Indices blanchiment
    indices_blanchiment: str | None = None
    # Section 7 — Identification (pré-rempli depuis KYC)
    identification: dict | None = None
    # Section 8 — Relations d'affaires
    relations_affaires: dict | None = None
    # Section 9 — Supports
    supports: SupportSchema | None = None
    # Section 10 — Autres
    autres_informations: str | None = None


class AddendumCreate(BaseModel):
    contenu: str


class AddendumOut(BaseModel):
    id: str
    dos_id: str
    user_id: str
    contenu: str
    created_at: str

    @classmethod
    def from_orm_safe(cls, obj) -> "AddendumOut":
        return cls(id=obj.id, dos_id=obj.dos_id, user_id=obj.user_id, contenu=obj.contenu,
                   created_at=obj.created_at.isoformat() if obj.created_at else "")


class DosOut(BaseModel):
    id: str
    dossier_id: str
    reference_interne: str
    statut: str
    organisme_libelle: str | None
    organisme_adresse: str | None
    organisme_email: str | None
    organisme_telephone: str | None
    type_soupcon_bc: bool
    type_soupcon_ft: bool
    type_soupcon_prolif: bool
    motifs: dict | None
    statut_operations: dict | None
    detail_transactions: dict | None
    indices_blanchiment: str | None
    identification: dict | None
    relations_affaires: dict | None
    supports: dict | None
    autres_informations: str | None
    initie_par: str
    valide_par: str | None
    soumis_at: str | None
    accuse_recu_at: str | None
    accuse_recu_ref: str | None
    created_at: str
    updated_at: str
    addendums: list[AddendumOut] = []

    @classmethod
    def from_orm_safe(cls, obj, addendums=None) -> "DosOut":
        return cls(
            id=obj.id, dossier_id=obj.dossier_id, reference_interne=obj.reference_interne,
            statut=obj.statut,
            organisme_libelle=obj.organisme_libelle, organisme_adresse=obj.organisme_adresse,
            organisme_email=obj.organisme_email, organisme_telephone=obj.organisme_telephone,
            type_soupcon_bc=obj.type_soupcon_bc, type_soupcon_ft=obj.type_soupcon_ft,
            type_soupcon_prolif=obj.type_soupcon_prolif,
            motifs=obj.motifs, statut_operations=obj.statut_operations,
            detail_transactions=obj.detail_transactions, indices_blanchiment=obj.indices_blanchiment,
            identification=obj.identification, relations_affaires=obj.relations_affaires,
            supports=obj.supports, autres_informations=obj.autres_informations,
            initie_par=obj.initie_par, valide_par=obj.valide_par,
            soumis_at=obj.soumis_at.isoformat() if obj.soumis_at else None,
            accuse_recu_at=obj.accuse_recu_at.isoformat() if obj.accuse_recu_at else None,
            accuse_recu_ref=obj.accuse_recu_ref,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            updated_at=obj.updated_at.isoformat() if obj.updated_at else "",
            addendums=[AddendumOut.from_orm_safe(a) for a in (addendums or [])],
        )
