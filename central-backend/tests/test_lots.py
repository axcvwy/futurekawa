# tests/test_lots.py
"""Création / mise à jour des lots : proxy local + règles de rôle."""


def test_creation_lot_interdite_pour_referent_qualite(client, utilisateurs, entrepot_bra):
    reponse = client.post(
        "/lots",
        headers=utilisateurs["qualite_bra"],
        json={
            "code_lot": "LOT-NOUVEAU",
            "entrepot_id": str(entrepot_bra.id),
            "produit": "Arabica",
            "quantite_kg": 100,
            "date_stockage": "2026-01-01",
        },
    )
    assert reponse.status_code == 403


def test_creation_lot_hors_perimetre_403(client, utilisateurs, entrepot_bra):
    reponse = client.post(
        "/lots",
        headers=utilisateurs["resp_col"],
        json={
            "code_lot": "LOT-HORS-PERIMETRE",
            "entrepot_id": str(entrepot_bra.id),
            "produit": "Arabica",
            "quantite_kg": 100,
            "date_stockage": "2026-01-01",
        },
    )
    assert reponse.status_code == 403


def test_creation_lot_mode_simulation_400(client, utilisateurs, pays_reference, entrepot_bra):
    # Le pays BRA est en mode mock : l'écriture proxy est refusée (pas de backend local).
    reponse = client.post(
        "/lots",
        headers=utilisateurs["resp_bra"],
        json={
            "code_lot": "LOT-SIMULE",
            "entrepot_id": str(entrepot_bra.id),
            "produit": "Arabica",
            "quantite_kg": 100,
            "date_stockage": "2026-01-01",
        },
    )
    assert reponse.status_code == 400


def test_referent_qualite_modifie_statut_seulement(client, utilisateurs, lot_bra, monkeypatch):
    # On court-circuite le proxy local : le lot central est déjà présent, on teste la règle métier.
    from app.routes import lot as route_lot

    monkeypatch.setattr(route_lot, "maj_lot_local", lambda *a, **k: {"ok": True})

    reponse = client.put(
        f"/lots/{lot_bra.id}",
        headers=utilisateurs["qualite_bra"],
        json={"statut": "A_VERIFIER"},
    )
    assert reponse.status_code == 200


def test_referent_qualite_refuse_quantite(client, utilisateurs, lot_bra, monkeypatch):
    from app.routes import lot as route_lot

    monkeypatch.setattr(route_lot, "maj_lot_local", lambda *a, **k: {"ok": True})

    reponse = client.put(
        f"/lots/{lot_bra.id}",
        headers=utilisateurs["qualite_bra"],
        json={"quantite_kg": 999},
    )
    assert reponse.status_code == 403


def test_referent_qualite_statut_autorise_uniquement(client, utilisateurs, lot_bra, monkeypatch):
    from app.routes import lot as route_lot

    monkeypatch.setattr(route_lot, "maj_lot_local", lambda *a, **k: {"ok": True})

    reponse = client.put(
        f"/lots/{lot_bra.id}",
        headers=utilisateurs["qualite_bra"],
        json={"statut": "EXPORTE"},
    )
    assert reponse.status_code == 400


def test_resp_entrepot_creation_dans_son_entrepot_autorisee(client, utilisateurs, entrepot_bra, monkeypatch):
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.lot import Lot
    from app.routes import lot as route_lot

    def faux_creer(db, pays_id, entrepot_central_id, corps):
        lot = Lot(
            pays_id=pays_id,
            entrepot_id=entrepot_central_id,
            source_id=uuid4(),
            code_lot=corps["code_lot"],
            produit=corps["produit"],
            quantite_kg=corps["quantite_kg"],
            date_stockage=corps["date_stockage"],
            statut=corps.get("statut", "EN_STOCK"),
            source_cree_le=datetime.now(timezone.utc),
            source_mis_a_jour_le=datetime.now(timezone.utc),
        )
        db.add(lot)
        db.commit()
        db.refresh(lot)
        return {"id": str(lot.id), "code_lot": lot.code_lot}

    monkeypatch.setattr(route_lot, "creer_lot_local", faux_creer)

    reponse = client.post(
        "/lots",
        headers=utilisateurs["resp_ent"],
        json={
            "code_lot": "LOT-ENTREPOT",
            "entrepot_id": str(entrepot_bra.id),
            "produit": "Arabica",
            "quantite_kg": 100,
            "date_stockage": "2026-01-01",
        },
    )
    assert reponse.status_code == 201


def test_resp_entrepot_creation_hors_entrepot_403(client, utilisateurs, entrepot_bra, exploitation_bra, pays_reference):
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.entrepot import Entrepot

    with SessionLocal() as db:
        autre = Entrepot(
            pays_id=pays_reference["BRA"].id,
            exploitation_id=exploitation_bra.id,
            source_id=uuid4(),
            nom="Entrepôt Rio",
            ville="Rio",
            code_pays="BRA",
            nom_responsable="João",
            email_responsable="joao@futurekawa.com",
            temperature_min_c=26.0,
            temperature_max_c=32.0,
            humidite_min_pct=53.0,
            humidite_max_pct=57.0,
            source_cree_le=datetime.now(timezone.utc),
            source_mis_a_jour_le=datetime.now(timezone.utc),
        )
        db.add(autre)
        db.commit()
        autre_id = autre.id

    reponse = client.post(
        "/lots",
        headers=utilisateurs["resp_ent"],
        json={
            "code_lot": "LOT-HORS",
            "entrepot_id": str(autre_id),
            "produit": "Arabica",
            "quantite_kg": 100,
            "date_stockage": "2026-01-01",
        },
    )
    assert reponse.status_code == 403
