# tests/test_ecritures.py
"""Écritures config (pays, exploitations, entrepôts, capteurs) : réservées à ADMIN_SIEGE."""


def test_non_admin_ne_peut_pas_configurer_pays(client, utilisateurs, pays_reference):
    reponse = client.put(
        f"/pays/{pays_reference['BRA'].id}",
        headers=utilisateurs["resp_bra"],
        json={"actif": False},
    )
    assert reponse.status_code == 403


def test_admin_peut_activer_desactiver_pays(client, en_tete_admin, pays_reference):
    reponse = client.put(
        f"/pays/{pays_reference['BRA'].id}",
        headers=en_tete_admin,
        json={"actif": False},
    )
    assert reponse.status_code == 200
    assert reponse.json()["actif"] is False


def test_creation_exploitation_admin(client, en_tete_admin, pays_reference):
    reponse = client.post(
        "/exploitations",
        headers=en_tete_admin,
        json={
            "pays_id": str(pays_reference["BRA"].id),
            "nom": "Fazenda Teste",
            "code": "FT",
            "ville": "Salvador",
            "actif": True,
        },
    )
    assert reponse.status_code == 201
    assert reponse.json()["code"] == "FT"


def test_creation_exploitation_reservee_admin(client, utilisateurs, pays_reference):
    reponse = client.post(
        "/exploitations",
        headers=utilisateurs["resp_bra"],
        json={
            "pays_id": str(pays_reference["BRA"].id),
            "nom": "Fazenda Teste",
            "code": "FT",
            "ville": "Salvador",
            "actif": True,
        },
    )
    assert reponse.status_code == 403


def test_reaffectation_entrepot_reservee_admin(client, utilisateurs, entrepot_bra, exploitation_bra, pays_reference):
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.exploitation import Exploitation

    with SessionLocal() as db:
        autre_explo = Exploitation(
            pays_id=pays_reference["BRA"].id,
            source_id=uuid4(),
            nom="Segunda Fazenda",
            code="SF",
            ville="Bahia",
            actif=True,
        )
        db.add(autre_explo)
        db.commit()
        autre_id = autre_explo.id

    reponse = client.put(
        f"/entrepots/{entrepot_bra.id}",
        headers=utilisateurs["resp_bra"],
        params={"exploitation_id": str(autre_id)},
    )
    assert reponse.status_code == 403


def test_reaffectation_entrepot_admin(client, en_tete_admin, entrepot_bra, pays_reference):
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.exploitation import Exploitation

    with SessionLocal() as db:
        autre_explo = Exploitation(
            pays_id=pays_reference["BRA"].id,
            source_id=uuid4(),
            nom="Segunda Fazenda",
            code="SF",
            ville="Bahia",
            actif=True,
        )
        db.add(autre_explo)
        db.commit()
        autre_id = autre_explo.id

    reponse = client.put(
        f"/entrepots/{entrepot_bra.id}",
        headers=en_tete_admin,
        params={"exploitation_id": str(autre_id)},
    )
    assert reponse.status_code == 200
    assert reponse.json()["exploitation_id"] == str(autre_id)


def test_creation_capteur_reservee_admin(client, utilisateurs, entrepot_bra):
    reponse = client.post(
        "/capteurs",
        headers=utilisateurs["resp_bra"],
        json={
            "entrepot_id": str(entrepot_bra.id),
            "reference": "CAP-NEW-001",
            "topic_mqtt": "futurekawa/bra/x",
            "type_capteur": "DHT22",
            "frequence_mesure_secondes": 30,
        },
    )
    assert reponse.status_code == 403
