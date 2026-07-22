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


class DosClasserRequest(BaseModel):
    motif: str


class DosAccuseRequest(BaseModel):
    reference_centif: str


class DosUpsert(BaseModel):
    # Section 1 — Organisme déclarant
    organisme_libelle: str | None = None
    organisme_adresse: str | None = None
    organisme_email: str | None = None
    organisme_telephone: str | None = None
    # Nature de l'opération suspecte (M3.1) + détection
    statut_operation: Literal["executee", "en_cours", "tentee"] | None = None
    date_detection: str | None = None
    # Section 3 — Type de soupçon (nature d'infraction M1.3 : Blanchiment / FT / Prolifération)
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
    statut_operation: str | None
    date_detection: str | None
    organisme_libelle: str | None
    organisme_adresse: str | None
    organisme_email: str | None
    organisme_telephone: str | None
    type_soupcon_bc: bool
    type_soupcon_ft: bool
    type_soupcon_prolif: bool
    motifs: dict | None
    statut_operations: dict | None
    # Section 5 : `DosUpsert` écrit une LISTE de transactions ; typer la sortie en
    # `dict` faisait échouer la validation Pydantic dès qu'une DOS était renseignée
    # (500 sur GET/PUT/soumettre/valider). Le `dict` reste toléré pour les DOS
    # héritées de la base MySQL, dont la section pouvait être un objet unique.
    detail_transactions: list[TransactionSchema] | dict | None
    indices_blanchiment: str | None
    identification: dict | None
    relations_affaires: dict | None
    supports: dict | None
    autres_informations: str | None
    decision: str | None
    motif_classement: str | None
    initie_par: str
    valide_par: str | None
    valide_par_rc: str | None
    valide_rc_at: str | None
    valide_par_dg: str | None
    valide_dg_at: str | None
    date_transmission_centif: str | None
    transmis_par: str | None
    soumis_at: str | None
    accuse_recu_at: str | None
    accuse_recu_ref: str | None
    accuse_alerte_j15_envoyee: bool = False
    created_at: str
    updated_at: str
    addendums: list[AddendumOut] = []

    @classmethod
    def from_orm_safe(cls, obj, addendums=None) -> "DosOut":
        return cls(
            id=obj.id, dossier_id=obj.dossier_id, reference_interne=obj.reference_interne,
            statut=obj.statut,
            statut_operation=obj.statut_operation,
            date_detection=obj.date_detection.isoformat() if obj.date_detection else None,
            organisme_libelle=obj.organisme_libelle, organisme_adresse=obj.organisme_adresse,
            organisme_email=obj.organisme_email, organisme_telephone=obj.organisme_telephone,
            type_soupcon_bc=obj.type_soupcon_bc, type_soupcon_ft=obj.type_soupcon_ft,
            type_soupcon_prolif=obj.type_soupcon_prolif,
            motifs=obj.motifs, statut_operations=obj.statut_operations,
            detail_transactions=obj.detail_transactions, indices_blanchiment=obj.indices_blanchiment,
            identification=obj.identification, relations_affaires=obj.relations_affaires,
            supports=obj.supports, autres_informations=obj.autres_informations,
            decision=obj.decision, motif_classement=obj.motif_classement,
            initie_par=obj.initie_par, valide_par=obj.valide_par,
            valide_par_rc=obj.valide_par_rc,
            valide_rc_at=obj.valide_rc_at.isoformat() if obj.valide_rc_at else None,
            valide_par_dg=obj.valide_par_dg,
            valide_dg_at=obj.valide_dg_at.isoformat() if obj.valide_dg_at else None,
            date_transmission_centif=obj.date_transmission_centif.isoformat() if obj.date_transmission_centif else None,
            transmis_par=obj.transmis_par,
            soumis_at=obj.soumis_at.isoformat() if obj.soumis_at else None,
            accuse_recu_at=obj.accuse_recu_at.isoformat() if obj.accuse_recu_at else None,
            accuse_recu_ref=obj.accuse_recu_ref,
            accuse_alerte_j15_envoyee=obj.accuse_alerte_j15_envoyee,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            updated_at=obj.updated_at.isoformat() if obj.updated_at else "",
            addendums=[AddendumOut.from_orm_safe(a) for a in (addendums or [])],
        )
