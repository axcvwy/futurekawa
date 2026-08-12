# app/services/erp_export.py
"""Export consolidé à destination d'un ERP (SAP / MS Dynamics / mock externe).

Le Siège expose une vue « progiciel de gestion » : stocks consolidés, alertes
qualité et historique de mesures, sans exposer le modèle interne (UUID, relations
pays/exploitation). Le consommateur externe s'authentifie par header X-ERP-Key
(voir app/core/security.verifier_cle_erp).
"""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.pays import Pays
from app.schemas import ERPAlerteOut, ERPMesureOut, ERPStockOut

SOURCE_NOM = "FutureKawa Central"


def _generated_at() -> datetime:
    return datetime.now(UTC)


def lister_stocks(db: Session) -> list[ERPStockOut]:
    """Stock FIFO consolidé : un lot par ligne, avec sa dernière mesure entrepôt
    et le nombre d'alertes ACTIVE attachées (vue ERP)."""

    nb_alertes_par_lot = dict(
        db.query(Alerte.lot_id, func.count(Alerte.id))
        .filter(Alerte.lot_id.isnot(None), Alerte.statut == "ACTIVE")
        .group_by(Alerte.lot_id)
        .all()
    )

    derniere_mesure_par_entrepot = {}
    lots = db.query(Lot).order_by(Lot.date_stockage.asc()).all()
    entrepots = {e.id: e for e in db.query(Entrepot).all()}
    pays = {p.id: p for p in db.query(Pays).all()}

    # Dernière mesure par entrepôt (index ix_mesures_entrepot_date)
    for entrepot_id in entrepots:
        derniere = (
            db.query(Mesure).filter(Mesure.entrepot_id == entrepot_id).order_by(Mesure.date_mesure.desc()).first()
        )
        if derniere is not None:
            derniere_mesure_par_entrepot[entrepot_id] = derniere

    result = []
    for lot in lots:
        entrepot = entrepots.get(lot.entrepot_id)
        pays_objet = pays.get(lot.pays_id)
        if entrepot is None or pays_objet is None:
            continue

        derniere = derniere_mesure_par_entrepot.get(lot.entrepot_id)
        result.append(
            ERPStockOut(
                lot_id=lot.code_lot,
                country_code=pays_objet.code_iso,
                country_name=pays_objet.nom,
                exploitation=entrepot.exploitation.nom if entrepot.exploitation else "",
                warehouse=entrepot.nom,
                product=lot.produit,
                quantity_kg=float(lot.quantite_kg),
                storage_date=lot.date_stockage,
                status=lot.statut,
                active_alert_count=nb_alertes_par_lot.get(lot.id, 0),
                last_temperature_c=float(derniere.temperature_c) if derniere else None,
                last_humidity_pct=float(derniere.humidite_pct) if derniere else None,
                last_sync_at=lot.synchronise_le,
            )
        )
    return result


def lister_alertes(db: Session) -> list[ERPAlerteOut]:
    """Alertes (qualité / conservation) consolidées, les plus récentes en tête."""
    alertes = db.query(Alerte).order_by(Alerte.date_declenchement.desc()).limit(1000).all()

    result = []
    for alerte in alertes:
        pays = db.get(Pays, alerte.pays_id) if alerte.pays_id else None
        entrepot = db.get(Entrepot, alerte.entrepot_id) if alerte.entrepot_id else None
        lot = db.get(Lot, alerte.lot_id) if alerte.lot_id else None
        result.append(
            ERPAlerteOut(
                lot_id=lot.code_lot if lot else None,
                country_code=pays.code_iso if pays else "",
                warehouse=entrepot.nom if entrepot else "",
                type=alerte.type_alerte,
                level=alerte.niveau,
                status=alerte.statut,
                message=alerte.message,
                detected_value=float(alerte.valeur_detectee) if alerte.valeur_detectee is not None else None,
                min_threshold=float(alerte.seuil_minimum) if alerte.seuil_minimum is not None else None,
                max_threshold=float(alerte.seuil_maximum) if alerte.seuil_maximum is not None else None,
                triggered_at=alerte.date_declenchement,
                resolved_at=alerte.date_resolution,
            )
        )
    return result


def lister_mesures(db: Session, entrepot_id: str | None = None, limite: int = 500) -> list[ERPMesureOut]:
    """Historique des télémesures IoT consolidé, ordonné du plus récent au plus ancien."""

    query = (
        db.query(Mesure, Entrepot, Pays, Capteur)
        .join(Entrepot, Mesure.entrepot_id == Entrepot.id)
        .join(Pays, Mesure.pays_id == Pays.id)
    )
    query = query.outerjoin(Capteur, Mesure.capteur_id == Capteur.id)
    if entrepot_id:
        query = query.filter(Mesure.entrepot_id == entrepot_id)
    lignes = query.order_by(Mesure.date_mesure.desc()).limit(min(limite, 5000)).all()

    result = []
    for mesure, entrepot, pays, capteur in lignes:
        result.append(
            ERPMesureOut(
                country_code=pays.code_iso,
                warehouse=entrepot.nom,
                warehouse_id=entrepot.id,
                sensor_reference=capteur.reference if capteur else None,
                source=mesure.source,
                topic_mqtt=mesure.topic_mqtt,
                recorded_at=mesure.date_mesure,
                temperature_c=float(mesure.temperature_c),
                humidity_pct=float(mesure.humidite_pct),
            )
        )
    return result
