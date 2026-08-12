# tests/test_erp.py
"""Flux d'intégration ERP : authentification X-ERP-Key + contrats de sortie."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.database.db import SessionLocal
from app.models.mesure import Mesure


@pytest.fixture
def cle_erp() -> dict:
    """En-tête authentifié pour un consommateur ERP (clé de dev)."""
    from app.config import ERP_API_KEY

    return {"X-ERP-Key": ERP_API_KEY}


def test_erp_sans_cle_repond_401(client):
    reponse = client.get("/erp/stocks")
    assert reponse.status_code == 401


def test_erp_avec_mauvaise_cle_repond_401(client):
    reponse = client.get("/erp/stocks", headers={"X-ERP-Key": "cle-invalide"})
    assert reponse.status_code == 401


def test_erp_stocks_consolides(client, cle_erp, lot_bra, alerte_bra, entrepot_bra, capteur_bra, pays_reference):
    with SessionLocal() as db:
        db.add(
            Mesure(
                pays_id=entrepot_bra.pays_id,
                entrepot_id=entrepot_bra.id,
                capteur_id=capteur_bra.id,
                lot_id=lot_bra.id,
                source_id=uuid4(),
                source="MQTT",
                topic_mqtt="futurekawa/bra/entrepot-1/temp",
                date_mesure=datetime.now(UTC),
                date_reception=datetime.now(UTC),
                temperature_c=30.2,
                humidite_pct=56.1,
                source_cree_le=datetime.now(UTC),
                source_mis_a_jour_le=datetime.now(UTC),
            )
        )
        db.commit()

    reponse = client.get("/erp/stocks", headers=cle_erp)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["source"] == "FutureKawa Central"
    assert corps["generated_at"] is not None
    assert len(corps["lots"]) == 1

    lot = corps["lots"][0]
    assert lot["lot_id"] == "LOT-BRA-2024-001"
    assert lot["country_code"] == "BRA"
    assert lot["country_name"] == "Brésil"
    assert lot["exploitation"] == "Fazenda Bahia"
    assert lot["warehouse"] == "Entrepôt Salvador"
    assert lot["product"] == "Arabica Bahia"
    assert lot["quantity_kg"] == 1200.0
    assert lot["status"] == "EN_STOCK"
    assert lot["active_alert_count"] == 1  # alerte_bra est ACTIVE
    assert lot["last_temperature_c"] == 30.2
    assert lot["last_humidity_pct"] == 56.1
    assert lot["last_sync_at"] is not None


def test_erp_stock_lot_inconnu_404(client, cle_erp):
    reponse = client.get("/erp/stocks/LOT-INCONNU", headers=cle_erp)
    assert reponse.status_code == 404


def test_erp_alertes_consolidees(client, cle_erp, alerte_bra):
    reponse = client.get("/erp/alertes", headers=cle_erp)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps["alertes"]) == 1
    alerte = corps["alertes"][0]
    assert alerte["type"] == "TEMPERATURE_ELEVEE"
    assert alerte["level"] == "ELEVE"
    assert alerte["status"] == "ACTIVE"
    assert alerte["lot_id"] == "LOT-BRA-2024-001"
    assert alerte["country_code"] == "BRA"
    assert alerte["detected_value"] == 34.5


def test_erp_mesures_historique(client, cle_erp, entrepot_bra, capteur_bra):
    with SessionLocal() as db:
        for i in range(2):
            db.add(
                Mesure(
                    pays_id=entrepot_bra.pays_id,
                    entrepot_id=entrepot_bra.id,
                    capteur_id=capteur_bra.id,
                    source_id=uuid4(),
                    source="MQTT",
                    topic_mqtt="futurekawa/bra/entrepot-1/temp",
                    date_mesure=datetime.now(UTC) - timedelta(minutes=i),
                    date_reception=datetime.now(UTC),
                    temperature_c=29.0 + i,
                    humidite_pct=55.0,
                    source_cree_le=datetime.now(UTC),
                    source_mis_a_jour_le=datetime.now(UTC),
                )
            )
        db.commit()

    reponse = client.get("/erp/mesures", headers=cle_erp)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps["mesures"]) == 2
    mesures = corps["mesures"]
    # Ordonnées du plus récent au plus ancien (29.0°C inséré à 'now', 30.0°C une minute avant)
    assert mesures[0]["temperature_c"] == 29.0
    assert mesures[1]["temperature_c"] == 30.0
    assert mesures[0]["warehouse"] == "Entrepôt Salvador"
    assert mesures[0]["country_code"] == "BRA"
    assert mesures[0]["sensor_reference"] == "CAP-BRA-001"
