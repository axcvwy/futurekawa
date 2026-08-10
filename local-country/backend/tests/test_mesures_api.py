# tests/test_mesures_api.py
"""Cas de tests API — POST /mesures/ (persistance par topic MQTT + clé API)."""

from app.models.mesure import Mesure


def test_post_mesures_persists_data_by_topic(client, en_tete_api, capteur_col, entrepot_col, db):
    """POST /mesures/ avec un topic connu → mesure persistée reliée au bon entrepôt/capteur."""
    corps = {
        "topic_mqtt": capteur_col.topic_mqtt,
        "temperature_c": 26.5,
        "humidite_pct": 80.0,
        "date_mesure": "2026-08-10T10:00:00Z",
    }
    reponse = client.post("/mesures/", headers=en_tete_api, json=corps)
    assert reponse.status_code == 201, reponse.text

    mesure = db.query(Mesure).one()
    assert mesure.entrepot_id == entrepot_col.id
    assert mesure.capteur_id == capteur_col.id
    assert mesure.topic_mqtt == capteur_col.topic_mqtt
    assert float(mesure.temperature_c) == 26.5
    assert float(mesure.humidite_pct) == 80.0


def test_post_mesures_unknown_topic_404(client, en_tete_api):
    """Topic MQTT inconnu → 404 capteur introuvable."""
    reponse = client.post(
        "/mesures/",
        headers=en_tete_api,
        json={"topic_mqtt": "futurekawa/col/inconnu", "temperature_c": 26.5, "humidite_pct": 80.0},
    )
    assert reponse.status_code == 404


def test_post_mesures_requires_api_key(client, capteur_col):
    """POST /mesures/ sans clé API → 401."""
    reponse = client.post(
        "/mesures/",
        json={
            "topic_mqtt": capteur_col.topic_mqtt,
            "temperature_c": 26.5,
            "humidite_pct": 80.0,
        },
    )
    assert reponse.status_code == 401


def test_post_mesures_incoherent_entrepot_400(client, en_tete_api, capteur_col, entrepot_col):
    """entrepot_id différent de celui du capteur → 400."""
    reponse = client.post(
        "/mesures/",
        headers=en_tete_api,
        json={
            "topic_mqtt": capteur_col.topic_mqtt,
            "entrepot_id": "00000000-0000-0000-0000-000000000000",
            "temperature_c": 26.5,
            "humidite_pct": 80.0,
        },
    )
    assert reponse.status_code == 400


def test_post_mesures_alerts_on_high_temperature(client, en_tete_api, capteur_col, db):
    """Température hors bande via l'API → alerte créée (circuit complet route + service)."""
    reponse = client.post(
        "/mesures/",
        headers=en_tete_api,
        json={"topic_mqtt": capteur_col.topic_mqtt, "temperature_c": 33.0, "humidite_pct": 80.0},
    )
    assert reponse.status_code == 201
    from app.models.alerte import Alerte

    assert db.query(Alerte).filter(Alerte.type_alerte == "TEMPERATURE_ELEVEE").count() == 1