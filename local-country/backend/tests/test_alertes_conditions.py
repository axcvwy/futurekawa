# tests/test_alertes_conditions.py
"""Cas de tests — logique de seuils température/humidité (backend local Colombie).

Bande idéale Colombie : 26 ± 3 °C (23–29 °C), humidité 80 ± 2 % (78–82 %).
"""

from app.models.alerte import Alerte
from app.services.alertes import detecter_anomalies_conditions


def _declencher(db, entrepot, capteur, lot, temp, hum):
    detecter_anomalies_conditions(
        db,
        entrepot=entrepot,
        capteur=capteur,
        lot=lot,
        temperature=temp,
        humidite=hum,
    )
    db.commit()


def test_temperature_normal_no_alert(db, entrepot_col, capteur_col, lot_col, _neutraliser_envoi_email):
    """26 °C / 80 % → aucune alerte, aucun e-mail."""
    _declencher(db, entrepot_col, capteur_col, lot_col, 26.0, 80.0)

    assert db.query(Alerte).count() == 0
    assert _neutraliser_envoi_email == []


def test_temperature_high_creates_one_alert_and_email(db, entrepot_col, capteur_col, lot_col, _neutraliser_envoi_email):
    """30 °C / 80 % → 1 alerte TEMPERATURE_ELEVEE ACTIVE + 1 e-mail."""
    _declencher(db, entrepot_col, capteur_col, lot_col, 30.0, 80.0)

    alertes = db.query(Alerte).all()
    assert len(alertes) == 1
    alerte = alertes[0]
    assert alerte.type_alerte == "TEMPERATURE_ELEVEE"
    assert alerte.statut == "ACTIVE"
    assert alerte.email_envoye is True
    assert alerte.date_email is not None
    assert float(alerte.valeur_detectee) == 30.0
    assert len(_neutraliser_envoi_email) == 1
    assert _neutraliser_envoi_email[0]["to"] == "tue131098@protonmail.com"


def test_repeated_high_temperature_does_not_duplicate_alerts_or_emails(
    db, entrepot_col, capteur_col, lot_col, _neutraliser_envoi_email
):
    """30 °C puis 31 °C → toujours 1 seule alerte ACTIVE et 1 seul e-mail."""
    _declencher(db, entrepot_col, capteur_col, lot_col, 30.0, 80.0)
    _declencher(db, entrepot_col, capteur_col, lot_col, 31.0, 80.0)

    alertes = db.query(Alerte).filter(Alerte.type_alerte == "TEMPERATURE_ELEVEE").all()
    actives = [a for a in alertes if a.statut == "ACTIVE"]
    assert len(alertes) == 1  # pas de doublon
    assert len(actives) == 1
    assert len(_neutraliser_envoi_email) == 1  # pas de 2e e-mail


def test_temperature_recovers_resolves_alert(db, entrepot_col, capteur_col, lot_col, _neutraliser_envoi_email):
    """Dérive haute puis retour à 26 °C → l'alerte passe RESOLUE avec date de résolution."""
    _declencher(db, entrepot_col, capteur_col, lot_col, 30.0, 80.0)
    _declencher(db, entrepot_col, capteur_col, lot_col, 26.0, 80.0)

    alertes = db.query(Alerte).filter(Alerte.type_alerte == "TEMPERATURE_ELEVEE").all()
    assert len(alertes) == 1
    assert alertes[0].statut == "RESOLUE"
    assert alertes[0].date_resolution is not None
    assert len(_neutraliser_envoi_email) == 1  # e-mail seulement à la première détection


def test_humidity_high_creates_alert(db, entrepot_col, capteur_col, lot_col, _neutraliser_envoi_email):
    """26 °C / 85 % → 1 alerte HUMIDITE_ELEVEE."""
    _declencher(db, entrepot_col, capteur_col, lot_col, 26.0, 85.0)

    alertes = db.query(Alerte).all()
    assert len(alertes) == 1
    assert alertes[0].type_alerte == "HUMIDITE_ELEVEE"
    assert alertes[0].statut == "ACTIVE"


def test_enregistre_la_mesure(db, entrepot_col, capteur_col, lot_col):
    """Chaque passage détecte aussi le contexte de mesure (persisté côté route)."""
    _declencher(db, entrepot_col, capteur_col, lot_col, 26.0, 80.0)
    # La mesure elle-même est persistée par la route /mesures ; ici on vérifie la non-création d'alerte.
    assert db.query(Alerte).count() == 0
