# tests/test_lots_anciens.py
"""Cas de tests — lot trop ancien (> 365 jours) → alerte LOT_TROP_ANCIEN + e-mail."""

from app.models.alerte import Alerte
from app.models.lot import Lot
from app.services.alertes import verifier_lots_anciens


def test_lot_trop_ancien_creates_alert(db, lot_ancien_col, _neutraliser_envoi_email):
    """Lot stocké depuis 366 jours → alerte LOT_TROP_ANCIEN + e-mail au responsable."""
    crees = verifier_lots_anciens(db)
    db.commit()

    assert crees == 1
    alertes = db.query(Alerte).filter(Alerte.type_alerte == "LOT_TROP_ANCIEN").all()
    assert len(alertes) == 1
    alerte = alertes[0]
    assert alerte.statut == "ACTIVE"
    assert alerte.capteur_id is None
    assert alerte.lot_id == lot_ancien_col.id
    assert float(alerte.valeur_detectee) == 366
    assert alerte.email_envoye is True
    assert len(_neutraliser_envoi_email) == 1
    assert _neutraliser_envoi_email[0]["to"] == "tue131098@protonmail.com"

    # Le lot EN_STOCK trop ancien passe PERIME
    lot_en_base = db.query(Lot).filter(Lot.id == lot_ancien_col.id).one()
    assert lot_en_base.statut == "PERIME"


def test_lot_trop_ancien_idempotent(db, lot_ancien_col, _neutraliser_envoi_email):
    """Deux passages → toujours 1 seule alerte et 1 seul e-mail (pas de doublon)."""
    verifier_lots_anciens(db)
    db.commit()
    verifier_lots_anciens(db)
    db.commit()

    alertes = db.query(Alerte).filter(Alerte.type_alerte == "LOT_TROP_ANCIEN").all()
    assert len(alertes) == 1
    assert len(_neutraliser_envoi_email) == 1


def test_lot_recent_no_alert(db, lot_col, _neutraliser_envoi_email):
    """Lot récent (< 365 jours) → aucune alerte, aucun e-mail."""
    crees = verifier_lots_anciens(db)
    db.commit()

    assert crees == 0
    assert db.query(Alerte).count() == 0
    assert _neutraliser_envoi_email == []
