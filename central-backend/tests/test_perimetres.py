# tests/test_perimetres.py
"""Restriction des données par rôle : pays / entrepôt / lots / alertes."""

from datetime import UTC


def test_admin_voit_tous_les_pays(client, en_tete_admin, pays_reference):
    reponse = client.get("/pays", headers=en_tete_admin)
    assert [p["code_iso"] for p in reponse.json()] == ["BRA", "COL", "ECU"]


def test_responsable_exploitation_ne_voit_que_son_pays(client, utilisateurs):
    reponse = client.get("/pays", headers=utilisateurs["resp_bra"])
    assert [p["code_iso"] for p in reponse.json()] == ["BRA"]


def test_referent_qualite_ne_voit_que_son_pays(client, utilisateurs):
    reponse = client.get("/pays", headers=utilisateurs["qualite_bra"])
    assert [p["code_iso"] for p in reponse.json()] == ["BRA"]


def test_responsable_entrepot_scope_entrepot(client, utilisateurs, entrepot_bra, exploitation_bra, pays_reference):
    # Création d'un second entrepôt BRA pour vérifier la restriction
    from datetime import datetime
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
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(autre)
        db.commit()

    reponse = client.get("/entrepots", headers=utilisateurs["resp_ent"])
    noms = [e["nom"] for e in reponse.json()]
    assert "Entrepôt Salvador" in noms
    assert "Entrepôt Rio" not in noms


def test_responsable_entrepot_scope_lots(client, utilisateurs, entrepot_bra, exploitation_bra, lot_bra, pays_reference):
    from datetime import datetime
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.entrepot import Entrepot
    from app.models.lot import Lot

    with SessionLocal() as db:
        autre_ent = Entrepot(
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
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(autre_ent)
        db.flush()
        autre_lot = Lot(
            pays_id=pays_reference["BRA"].id,
            entrepot_id=autre_ent.id,
            source_id=uuid4(),
            code_lot="LOT-BRA-RIO-001",
            produit="Robusta",
            quantite_kg=500.0,
            date_stockage=__import__("datetime").date(2024, 2, 1),
            statut="EN_STOCK",
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(autre_lot)
        db.commit()

    reponse = client.get("/lots", headers=utilisateurs["resp_ent"])
    codes = [lot["code_lot"] for lot in reponse.json()]
    assert "LOT-BRA-2024-001" in codes
    assert "LOT-BRA-RIO-001" not in codes


def test_lot_du_pays_col_invisible_pour_resp_bra(client, utilisateurs, pays_reference, entrepot_bra, lot_bra):
    from datetime import datetime
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.entrepot import Entrepot
    from app.models.exploitation import Exploitation
    from app.models.lot import Lot

    with SessionLocal() as db:
        explo_col = Exploitation(
            pays_id=pays_reference["COL"].id,
            source_id=uuid4(),
            nom="Finca Antioquia",
            code="FA",
            ville="Medellín",
            actif=True,
        )
        db.add(explo_col)
        db.flush()
        ent_col = Entrepot(
            pays_id=pays_reference["COL"].id,
            exploitation_id=explo_col.id,
            source_id=uuid4(),
            nom="Bodega Medellín",
            ville="Medellín",
            code_pays="COL",
            nom_responsable="Lucía",
            email_responsable="lucia@futurekawa.com",
            temperature_min_c=23.0,
            temperature_max_c=29.0,
            humidite_min_pct=78.0,
            humidite_max_pct=82.0,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(ent_col)
        db.flush()
        lot_col = Lot(
            pays_id=pays_reference["COL"].id,
            entrepot_id=ent_col.id,
            source_id=uuid4(),
            code_lot="LOT-COL-001",
            produit="Castillo",
            quantite_kg=800.0,
            date_stockage=__import__("datetime").date(2024, 3, 5),
            statut="EN_STOCK",
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(lot_col)
        db.commit()

    reponse = client.get("/lots", headers=utilisateurs["resp_bra"])
    codes = [lot["code_lot"] for lot in reponse.json()]
    assert "LOT-BRA-2024-001" in codes
    assert "LOT-COL-001" not in codes


def test_alerte_hors_perimetre_invisible(client, utilisateurs, pays_reference, entrepot_bra, alerte_bra):
    from datetime import datetime
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.alerte import Alerte
    from app.models.capteur import Capteur

    with SessionLocal() as db:
        capteur_col = Capteur(
            pays_id=pays_reference["COL"].id,
            entrepot_id=entrepot_bra.id,  # entrepôt différent, mais pays COL
            source_id=uuid4(),
            reference="CAP-COL-001",
            topic_mqtt="futurekawa/col/x",
            type_capteur="DHT22",
            statut="ACTIF",
            frequence_mesure_secondes=60,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(capteur_col)
        db.flush()
        alerte_col = Alerte(
            pays_id=pays_reference["COL"].id,
            entrepot_id=entrepot_bra.id,
            lot_id=None,
            capteur_id=capteur_col.id,
            source_id=uuid4(),
            type_alerte="HUMIDITE_ELEVEE",
            niveau="ELEVE",
            statut="ACTIVE",
            message="Humidité COL",
            valeur_detectee=85.0,
            seuil_minimum=78.0,
            seuil_maximum=82.0,
            date_declenchement=datetime.now(UTC),
            email_envoye=False,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(alerte_col)
        db.commit()

    reponse = client.get("/alertes", headers=utilisateurs["resp_bra"])
    assert all(a["pays"]["code_iso"] == "BRA" for a in reponse.json())


def test_responsable_entrepot_ne_voit_que_ses_alertes(
    client, utilisateurs, alerte_bra, entrepot_bra, exploitation_bra, pays_reference
):
    from datetime import datetime
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.alerte import Alerte
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
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(autre)
        db.flush()
        alerte_autre = Alerte(
            pays_id=pays_reference["BRA"].id,
            entrepot_id=autre.id,
            lot_id=None,
            capteur_id=None,
            source_id=uuid4(),
            type_alerte="LOT_TROP_ANCIEN",
            niveau="MOYEN",
            statut="ACTIVE",
            message="Lot ancien Rio",
            valeur_detectee=400.0,
            seuil_minimum=365.0,
            seuil_maximum=None,
            date_declenchement=datetime.now(UTC),
            email_envoye=False,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(alerte_autre)
        db.commit()

    reponse = client.get("/alertes", headers=utilisateurs["resp_ent"])
    noms = [a["entrepot"]["nom"] for a in reponse.json()]
    assert "Entrepôt Salvador" in noms
    assert "Entrepôt Rio" not in noms
