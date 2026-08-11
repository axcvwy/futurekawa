# app/services/syncer.py
"""
Moteur de synchronisation : tire les données de chaque backend local (par pays),
les consolide dans la base PostgreSQL centrale via des upserts idempotents (pays_id, source_id).

Ordre de synchro imposé par les contraintes de clés étrangères :
1. entrepots  2. capteurs  3. lots  4. mesures  5. alertes
"""

import datetime
import logging
import uuid

import requests
from sqlalchemy.orm import Session

from app.config import SYNC_OVERLAP_SECONDS, SYNC_PAGE_SIZE, SYNC_REQUEST_TIMEOUT
from app.mock_data import MOCK_PAYS
from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.exploitation import Exploitation
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.pays import Pays
from app.models.synchronisation import Synchronisation

logger = logging.getLogger(__name__)


# Helpers de conversion
def to_uuid(value):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        logger.warning("Date illisible ignorée : %s", value)
        return None


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# Pagination des API locales
def extract_items(payload):
    """Extrait la liste d'enregistrements quel que soit le format JSON retourné."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "records", "entrepots", "capteurs", "lots", "mesures", "alertes"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def has_more_pages(payload, items, offset, page_size):
    if len(items) < page_size:
        return False
    if isinstance(payload, dict):
        pagination = payload.get("pagination")
        if isinstance(pagination, dict) and "has_more" in pagination:
            return bool(pagination.get("has_more"))
        total = payload.get("total") or payload.get("count")
        if total is not None:
            return offset + len(items) < int(total)
    return True


def fetch_all(pays: Pays, resource: str, cursor: datetime.datetime | None):
    """Itère sur toutes les pages d'une ressource locale filtrée par mis_a_jour_depuis."""
    headers = {"X-API-Key": pays.api_key}
    params = {"limit": SYNC_PAGE_SIZE, "offset": 0}
    if cursor is not None:
        params["mis_a_jour_depuis"] = cursor.isoformat()

    url = f"{pays.api_base_url.rstrip('/')}/{resource}/"
    while True:
        response = requests.get(url, headers=headers, params=params, timeout=SYNC_REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        items = extract_items(payload)
        yield from items
        if not has_more_pages(payload, items, params["offset"], SYNC_PAGE_SIZE):
            break
        params["offset"] += len(items)


def _items(state: "_SyncState", resource: str, cursor: datetime.datetime | None):
    """Source des enregistrements : données simulées (pays mock) ou API locale (HTTP)."""
    if state.pays.mock:
        return iter(MOCK_PAYS.get(state.pays.code_iso, {}).get(resource, []))
    return fetch_all(state.pays, resource, cursor)


# État de synchronisation d'un pays (caches de mapping + curseur)
class _SyncState:
    def __init__(self, db: Session, pays: Pays, now: datetime.datetime):
        self.db = db
        self.pays = pays
        self.now = now
        self.exploitation = _ensure_default_exploitation(db, pays)
        self.entrepot_cache: dict[str, uuid.UUID] = {}
        self.capteur_cache: dict[str, uuid.UUID] = {}
        self.lot_cache: dict[str, uuid.UUID] = {}
        self.curseur_arrivee: datetime.datetime | None = None

    def track(self, value: datetime.datetime | None):
        if value is None:
            return
        if self.curseur_arrivee is None or value > self.curseur_arrivee:
            self.curseur_arrivee = value

    def _resolve(self, model, cache: dict, source_id):
        """Retrouve l'ID central associé à un UUID local (via la BDD si non en cache)."""
        local_id = to_uuid(source_id)
        if local_id is None:
            return None
        key = str(local_id)
        if key not in cache:
            row = (
                self.db.query(model)
                .filter(
                    model.pays_id == self.pays.id,
                    model.source_id == local_id,
                )
                .first()
            )
            cache[key] = row.id if row else None
        return cache[key]

    def central_entrepot(self, source_id):
        return self._resolve(Entrepot, self.entrepot_cache, source_id)

    def central_capteur(self, source_id):
        return self._resolve(Capteur, self.capteur_cache, source_id)

    def central_lot(self, source_id):
        return self._resolve(Lot, self.lot_cache, source_id)

    def upsert(self, model, source_id, values: dict):
        """Insertion ou mise à jour idempotente sur (pays_id, source_id)."""
        local_id = to_uuid(source_id)
        if local_id is None:
            return None
        row = (
            self.db.query(model)
            .filter(
                model.pays_id == self.pays.id,
                model.source_id == local_id,
            )
            .first()
        )
        if row is None:
            row = model(pays_id=self.pays.id, source_id=local_id)
            self.db.add(row)
        for key, value in values.items():
            setattr(row, key, value)
        if row.id is None:
            self.db.flush()  # Insère avec toutes les valeurs et assigne l'id central (mapping intra-run)
        return row


def _ensure_default_exploitation(db: Session, pays: Pays) -> Exploitation:
    """Crée l'exploitation par défaut du pays si aucune n'existe (les API locales n'en exposent pas)."""
    exploitation = db.query(Exploitation).filter_by(pays_id=pays.id).first()
    if exploitation is None:
        exploitation = Exploitation(
            pays_id=pays.id,
            nom=f"Exploitation principale {pays.nom}",
            code=f"EXPL-{pays.code_iso}",
            ville=None,
            actif=True,
        )
        db.add(exploitation)
        db.flush()
    return exploitation


# Étapes de synchronisation (1 par table)
def _sync_entrepots(state: _SyncState, cursor):
    lus = ecrits = 0
    for item in _items(state, "entrepots", cursor):
        lus += 1
        values = {
            "exploitation_id": state.exploitation.id,
            "nom": item.get("nom"),
            "ville": item.get("ville"),
            "code_pays": item.get("code_pays"),
            "nom_responsable": item.get("nom_responsable"),
            "email_responsable": item.get("email_responsable"),
            "temperature_min_c": item.get("temperature_min_c"),
            "temperature_max_c": item.get("temperature_max_c"),
            "humidite_min_pct": item.get("humidite_min_pct"),
            "humidite_max_pct": item.get("humidite_max_pct"),
            "source_cree_le": parse_datetime(item.get("cree_le")) or state.now,
            "source_mis_a_jour_le": parse_datetime(item.get("mis_a_jour_le")) or state.now,
            "synchronise_le": state.now,
        }
        row = state.upsert(Entrepot, item.get("id"), values)
        if row is None:
            continue
        state.entrepot_cache[str(to_uuid(item.get("id")))] = row.id
        state.track(parse_datetime(item.get("mis_a_jour_le")))
        ecrits += 1
    return lus, ecrits


def _sync_capteurs(state: _SyncState, cursor):
    lus = ecrits = 0
    for item in _items(state, "capteurs", cursor):
        lus += 1
        entrepot_id = state.central_entrepot(item.get("entrepot_id"))
        if entrepot_id is None:
            logger.warning("Capteur %s : entrepot source introuvable, ignoré", item.get("id"))
            continue
        values = {
            "entrepot_id": entrepot_id,
            "reference": item.get("reference"),
            "topic_mqtt": item.get("topic_mqtt"),
            "type_capteur": item.get("type_capteur"),
            "statut": item.get("statut", "ACTIF"),
            "frequence_mesure_secondes": item.get("frequence_mesure_secondes"),
            "derniere_communication": parse_datetime(item.get("derniere_communication")),
            "source_cree_le": parse_datetime(item.get("cree_le")) or state.now,
            "source_mis_a_jour_le": parse_datetime(item.get("mis_a_jour_le")) or state.now,
            "synchronise_le": state.now,
        }
        row = state.upsert(Capteur, item.get("id"), values)
        if row is None:
            continue
        state.capteur_cache[str(to_uuid(item.get("id")))] = row.id
        state.track(parse_datetime(item.get("mis_a_jour_le")))
        ecrits += 1
    return lus, ecrits


def _sync_lots(state: _SyncState, cursor):
    lus = ecrits = 0
    for item in _items(state, "lots", cursor):
        lus += 1
        entrepot_id = state.central_entrepot(item.get("entrepot_id"))
        if entrepot_id is None:
            logger.warning("Lot %s : entrepot source introuvable, ignoré", item.get("id"))
            continue
        values = {
            "entrepot_id": entrepot_id,
            "code_lot": item.get("code_lot"),
            "produit": item.get("produit"),
            "quantite_kg": item.get("quantite_kg"),
            "date_stockage": parse_date(item.get("date_stockage")),
            "statut": item.get("statut", "EN_STOCK"),
            "source_cree_le": parse_datetime(item.get("cree_le")) or state.now,
            "source_mis_a_jour_le": parse_datetime(item.get("mis_a_jour_le")) or state.now,
            "synchronise_le": state.now,
        }
        row = state.upsert(Lot, item.get("id"), values)
        if row is None:
            continue
        state.lot_cache[str(to_uuid(item.get("id")))] = row.id
        state.track(parse_datetime(item.get("mis_a_jour_le")))
        ecrits += 1
    return lus, ecrits


def _sync_mesures(state: _SyncState, cursor):
    lus = ecrits = 0
    for item in _items(state, "mesures", cursor):
        lus += 1
        entrepot_id = state.central_entrepot(item.get("entrepot_id"))
        capteur_id = state.central_capteur(item.get("capteur_id"))
        if entrepot_id is None or capteur_id is None:
            continue
        values = {
            "entrepot_id": entrepot_id,
            "capteur_id": capteur_id,
            "lot_id": state.central_lot(item.get("lot_id")),
            "source": item.get("source", "MQTT"),
            "topic_mqtt": item.get("topic_mqtt"),
            "date_mesure": parse_datetime(item.get("date_mesure")) or state.now,
            "date_reception": parse_datetime(item.get("date_reception")) or state.now,
            "temperature_c": item.get("temperature_c"),
            "humidite_pct": item.get("humidite_pct"),
            "donnees_brutes": item.get("donnees_brutes"),
            "source_cree_le": parse_datetime(item.get("cree_le")) or state.now,
            "source_mis_a_jour_le": parse_datetime(item.get("mis_a_jour_le")) or state.now,
            "synchronise_le": state.now,
        }
        if state.upsert(Mesure, item.get("id"), values) is None:
            continue
        state.track(parse_datetime(item.get("mis_a_jour_le")))
        ecrits += 1
    return lus, ecrits


def _sync_alertes(state: _SyncState, cursor):
    lus = ecrits = 0
    for item in _items(state, "alertes", cursor):
        lus += 1
        entrepot_id = state.central_entrepot(item.get("entrepot_id"))
        if entrepot_id is None:
            continue
        values = {
            "entrepot_id": entrepot_id,
            "lot_id": state.central_lot(item.get("lot_id")),
            "capteur_id": state.central_capteur(item.get("capteur_id")),
            "type_alerte": item.get("type_alerte"),
            "niveau": item.get("niveau", "MOYEN"),
            "statut": item.get("statut", "ACTIVE"),
            "message": item.get("message"),
            "valeur_detectee": item.get("valeur_detectee"),
            "seuil_minimum": item.get("seuil_minimum"),
            "seuil_maximum": item.get("seuil_maximum"),
            "date_declenchement": parse_datetime(item.get("date_declenchement")) or state.now,
            "date_resolution": parse_datetime(item.get("date_resolution")),
            "resolue_par": to_uuid(item.get("resolue_par")),
            "commentaire_resolution": item.get("commentaire_resolution"),
            "email_envoye": item.get("email_envoye", False),
            "date_email": parse_datetime(item.get("date_email")),
            "source_cree_le": parse_datetime(item.get("cree_le")) or state.now,
            "source_mis_a_jour_le": parse_datetime(item.get("mis_a_jour_le")) or state.now,
            "synchronise_le": state.now,
        }
        if state.upsert(Alerte, item.get("id"), values) is None:
            continue
        state.track(parse_datetime(item.get("mis_a_jour_le")))
        ecrits += 1
    return lus, ecrits


_STAGE_FUNCS = {
    "entrepots": _sync_entrepots,
    "capteurs": _sync_capteurs,
    "lots": _sync_lots,
    "mesures": _sync_mesures,
    "alertes": _sync_alertes,
}

# Correspondance étape -> colonnes de compteurs de la table synchronisations
_COUNT_COLUMNS = {
    "entrepots": ("entrepots_lus", "entrepots_ecrits"),
    "capteurs": ("capteurs_lus", "capteurs_ecrits"),
    "lots": ("lots_lus", "lots_ecrits"),
    "mesures": ("mesures_lues", "mesures_ecrites"),
    "alertes": ("alertes_lues", "alertes_ecrites"),
}


# Exécution complète d'une synchronisation pays
def compute_cursor(db: Session, pays: Pays) -> datetime.datetime | None:
    """Curseur = dernière synchro réussie - fenêtre de recouvrement (anti-frontière)."""
    ref = pays.derniere_sync_reussie_le
    if ref is None:
        last_run = (
            db.query(Synchronisation)
            .filter(
                Synchronisation.pays_id == pays.id,
                Synchronisation.statut == "SUCCES",
                Synchronisation.curseur_arrivee.isnot(None),
            )
            .order_by(Synchronisation.terminee_le.desc())
            .first()
        )
        if last_run is not None:
            ref = last_run.curseur_arrivee
    if ref is None:
        return None
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=datetime.UTC)
    return ref - datetime.timedelta(seconds=SYNC_OVERLAP_SECONDS)


def synchronize_pays(db: Session, pays: Pays, declencheur: str = "AUTOMATIQUE") -> Synchronisation:
    """Synchronise un pays depuis son API locale et met à jour son statut.

    La transaction est laissée au soin de l'appelant (commit/rollback).
    """
    now = datetime.datetime.now(datetime.UTC)
    cursor = compute_cursor(db, pays)

    run = Synchronisation(
        pays_id=pays.id,
        declencheur=declencheur,
        statut="EN_COURS",
        demarree_le=now,
        curseur_depart=cursor,
    )
    db.add(run)
    db.flush()

    state = _SyncState(db, pays, now)
    counts = {name: (0, 0) for name in _STAGE_FUNCS}

    erreur = None
    try:
        for name in _STAGE_FUNCS:
            lus, ecrits = _STAGE_FUNCS[name](state, cursor)
            counts[name] = (lus, ecrits)
            db.flush()
    except Exception as exc:  # Coupure réseau, 401, 5xx... => visible dans /pays et /health
        erreur = f"{exc.__class__.__name__}: {exc}"
        logger.exception("Synchronisation %s (%s) en échec", pays.code_iso, declencheur)

    for name, (lus, ecrits) in counts.items():
        setattr(run, _COUNT_COLUMNS[name][0], lus)
        setattr(run, _COUNT_COLUMNS[name][1], ecrits)

    run.terminee_le = datetime.datetime.now(datetime.UTC)
    run.curseur_arrivee = state.curseur_arrivee
    run.erreur = erreur

    if erreur is None:
        run.statut = "SUCCES"
        pays.dernier_statut_sync = "SUCCES"
        pays.derniere_sync_reussie_le = run.terminee_le
        pays.derniere_erreur_sync = None
    elif counts["entrepots"][1] > 0:
        run.statut = "SUCCES_PARTIEL"
        pays.dernier_statut_sync = "SUCCES_PARTIEL"
        pays.derniere_erreur_sync = erreur
    else:
        run.statut = "ECHEC"
        pays.dernier_statut_sync = "ECHEC"
        pays.derniere_erreur_sync = erreur

    db.flush()
    return run
