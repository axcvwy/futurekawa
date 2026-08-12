# app/schemas.py
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PaysOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nom: str
    code_iso: str
    api_base_url: str
    actif: bool
    mock: bool
    intervalle_sync_secondes: int
    temperature_cible_c: float | None = None
    humidite_cible_pct: float | None = None
    tolerance_temperature_c: float | None = None
    tolerance_humidite_pct: float | None = None
    derniere_sync_reussie_le: datetime | None = None
    dernier_statut_sync: str
    derniere_erreur_sync: str | None = None
    cree_le: datetime
    mis_a_jour_le: datetime


class ExploitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    source_id: uuid.UUID | None = None
    nom: str
    code: str
    ville: str | None = None
    actif: bool
    cree_le: datetime
    mis_a_jour_le: datetime


class EntrepotCreate(BaseModel):
    pays_id: uuid.UUID
    nom: str
    ville: str
    nom_responsable: str
    email_responsable: str
    temperature_min_c: float
    temperature_max_c: float
    humidite_min_pct: float
    humidite_max_pct: float


class EntrepotUpdate(BaseModel):
    nom: str | None = None
    ville: str | None = None
    nom_responsable: str | None = None
    email_responsable: str | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    humidite_min_pct: float | None = None
    humidite_max_pct: float | None = None


class EntrepotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    exploitation_id: uuid.UUID
    source_id: uuid.UUID
    nom: str
    ville: str
    code_pays: str
    nom_responsable: str
    email_responsable: str
    temperature_min_c: float
    temperature_max_c: float
    humidite_min_pct: float
    humidite_max_pct: float
    source_cree_le: datetime
    source_mis_a_jour_le: datetime
    synchronise_le: datetime
    cree_le: datetime
    mis_a_jour_le: datetime


class CapteurOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    entrepot_id: uuid.UUID
    source_id: uuid.UUID
    reference: str
    topic_mqtt: str
    type_capteur: str
    statut: str
    frequence_mesure_secondes: int
    derniere_communication: datetime | None = None
    source_cree_le: datetime
    source_mis_a_jour_le: datetime
    synchronise_le: datetime
    cree_le: datetime
    mis_a_jour_le: datetime


class CapteurCreate(BaseModel):
    entrepot_id: uuid.UUID
    reference: str
    topic_mqtt: str
    type_capteur: str
    statut: str = "ACTIF"
    frequence_mesure_secondes: int


class CapteurUpdate(BaseModel):
    entrepot_id: uuid.UUID | None = None
    reference: str | None = None
    topic_mqtt: str | None = None
    type_capteur: str | None = None
    statut: str | None = None
    frequence_mesure_secondes: int | None = None


class LotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    entrepot_id: uuid.UUID
    source_id: uuid.UUID
    code_lot: str
    produit: str
    quantite_kg: float
    date_stockage: date
    statut: str
    source_cree_le: datetime
    source_mis_a_jour_le: datetime
    synchronise_le: datetime
    cree_le: datetime
    mis_a_jour_le: datetime


class LotCreate(BaseModel):
    code_lot: str
    entrepot_id: uuid.UUID
    produit: str
    quantite_kg: float
    date_stockage: date
    statut: str = "EN_STOCK"


class LotUpdate(BaseModel):
    code_lot: str | None = None
    entrepot_id: uuid.UUID | None = None
    produit: str | None = None
    quantite_kg: float | None = None
    date_stockage: date | None = None
    statut: str | None = None


class MesureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    entrepot_id: uuid.UUID
    capteur_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    source_id: uuid.UUID
    source: str
    topic_mqtt: str
    date_mesure: datetime
    date_reception: datetime
    temperature_c: float
    humidite_pct: float
    donnees_brutes: dict | None = None
    source_cree_le: datetime
    source_mis_a_jour_le: datetime
    synchronise_le: datetime
    cree_le: datetime
    mis_a_jour_le: datetime


class AlerteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    entrepot_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    capteur_id: uuid.UUID | None = None
    source_id: uuid.UUID
    type_alerte: str
    niveau: str
    statut: str
    message: str
    valeur_detectee: float | None = None
    seuil_minimum: float | None = None
    seuil_maximum: float | None = None
    date_declenchement: datetime
    date_resolution: datetime | None = None
    resolue_par: uuid.UUID | None = None
    commentaire_resolution: str | None = None
    email_envoye: bool
    date_email: datetime | None = None
    source_cree_le: datetime
    source_mis_a_jour_le: datetime
    synchronise_le: datetime
    cree_le: datetime
    mis_a_jour_le: datetime


class SynchronisationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pays_id: uuid.UUID
    declencheur: str
    statut: str
    demarree_le: datetime
    terminee_le: datetime | None = None
    curseur_depart: datetime | None = None
    curseur_arrivee: datetime | None = None
    entrepots_lus: int
    entrepots_ecrits: int
    capteurs_lus: int
    capteurs_ecrits: int
    lots_lus: int
    lots_ecrits: int
    mesures_lues: int
    mesures_ecrites: int
    alertes_lues: int
    alertes_ecrites: int
    erreur: str | None = None
    cree_le: datetime
    mis_a_jour_le: datetime


class PaysRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nom: str
    code_iso: str


class EntrepotRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nom: str
    ville: str


class ExploitationRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nom: str
    code: str


class LotDetailOut(LotOut):
    entrepot: EntrepotRef | None = None
    pays: PaysRef | None = None
    exploitation: ExploitationRef | None = None


class AlerteDetailOut(AlerteOut):
    pays: PaysRef | None = None
    entrepot: EntrepotRef | None = None


class EntrepotDetailOut(EntrepotOut):
    pays: PaysRef | None = None
    exploitation: ExploitationRef | None = None


class PaysUpdate(BaseModel):
    actif: bool | None = None
    intervalle_sync_secondes: int | None = None
    api_base_url: str | None = None


class ExploitationCreate(BaseModel):
    pays_id: uuid.UUID
    nom: str
    code: str
    ville: str | None = None
    actif: bool = True


class AlerteUpdate(BaseModel):
    statut: str
    commentaire_resolution: str | None = None


class LoginRequest(BaseModel):
    email: str
    mot_de_passe: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilisateur: "UtilisateurOut"


class UtilisateurOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nom: str
    role: str
    actif: bool
    pays_id: uuid.UUID | None = None
    entrepot_id: uuid.UUID | None = None
    cree_le: datetime
    mis_a_jour_le: datetime


class UtilisateurCreate(BaseModel):
    email: str
    nom: str
    mot_de_passe: str
    role: str
    actif: bool = True
    pays_id: uuid.UUID | None = None
    entrepot_id: uuid.UUID | None = None


class UtilisateurUpdate(BaseModel):
    nom: str | None = None
    mot_de_passe: str | None = None
    role: str | None = None
    actif: bool | None = None
    pays_id: uuid.UUID | None = None
    entrepot_id: uuid.UUID | None = None


class MessageResponse(BaseModel):
    message: str

#  Schémas du flux d'intégration ERP (machine-to-machine, X-ERP-Key)

class ERPStockOut(BaseModel):
    """Stock consolidé, vu par l'ERP (un lot = une ligne)."""

    lot_id: str  # code_lot du pays (identifiant métier partagé)
    country_code: str
    country_name: str
    exploitation: str
    warehouse: str
    product: str
    quantity_kg: float
    storage_date: date
    status: str
    active_alert_count: int
    last_temperature_c: float | None = None
    last_humidity_pct: float | None = None
    last_sync_at: datetime


class ERPAlerteOut(BaseModel):
    """Exception qualité / conservation, vue par l'ERP."""

    lot_id: str | None
    country_code: str
    warehouse: str
    type: str
    level: str
    status: str
    message: str
    detected_value: float | None = None
    min_threshold: float | None = None
    max_threshold: float | None = None
    triggered_at: datetime
    resolved_at: datetime | None = None


class ERPMesureOut(BaseModel):
    """Historique de mesures d'un entrepôt, vu par l'ERP."""

    country_code: str
    warehouse: str
    warehouse_id: uuid.UUID  # référence interne, utile pour le rapprochement ERP
    sensor_reference: str | None = None
    source: str
    topic_mqtt: str
    recorded_at: datetime
    temperature_c: float
    humidity_pct: float


class ERPStockListOut(BaseModel):
    generated_at: datetime
    source: str
    lots: list[ERPStockOut]


class ERPAlerteListOut(BaseModel):
    generated_at: datetime
    source: str
    alertes: list[ERPAlerteOut]


class ERPMesureListOut(BaseModel):
    generated_at: datetime
    source: str
    mesures: list[ERPMesureOut]
