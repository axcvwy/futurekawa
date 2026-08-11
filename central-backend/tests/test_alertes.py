# tests/test_alertes.py
"""Règles de traitement des alertes par rôle."""

from datetime import UTC


def test_statut_invalide_400(client, en_tete_admin, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=en_tete_admin,
        json={"statut": "EXPLOSE"},
    )
    assert reponse.status_code == 400


def test_admin_resout_une_alerte(client, en_tete_admin, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=en_tete_admin,
        json={"statut": "RESOLUE", "commentaire_resolution": "Capteur recalibré"},
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "RESOLUE"
    assert corps["commentaire_resolution"] == "Capteur recalibré"
    assert corps["date_resolution"] is not None


def test_qualite_resout_dans_son_pays(client, utilisateurs, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=utilisateurs["qualite_bra"],
        json={"statut": "RESOLUE"},
    )
    assert reponse.status_code == 200


def test_resp_exploitation_ignore_dans_son_pays(client, utilisateurs, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=utilisateurs["resp_bra"],
        json={"statut": "IGNOREE"},
    )
    assert reponse.status_code == 200


def test_resp_entrepot_peut_acquitter(client, utilisateurs, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=utilisateurs["resp_ent"],
        json={"statut": "PRISE_EN_COMPTE"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "PRISE_EN_COMPTE"


def test_resp_entrepot_ne_peut_pas_resoudre(client, utilisateurs, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=utilisateurs["resp_ent"],
        json={"statut": "RESOLUE"},
    )
    assert reponse.status_code == 403


def test_resp_entrepot_ne_peut_pas_ignorer(client, utilisateurs, alerte_bra):
    reponse = client.patch(
        f"/alertes/{alerte_bra.id}",
        headers=utilisateurs["resp_ent"],
        json={"statut": "IGNOREE"},
    )
    assert reponse.status_code == 403


def test_alerte_hors_pays_403_pour_qualite_col(client, utilisateurs, alerte_bra, pays_reference, entrepot_bra):
    from datetime import datetime
    from uuid import uuid4

    from app.database.db import SessionLocal
    from app.models.alerte import Alerte

    with SessionLocal() as db:
        alerte_col = Alerte(
            pays_id=pays_reference["COL"].id,
            entrepot_id=entrepot_bra.id,
            lot_id=None,
            capteur_id=None,
            source_id=uuid4(),
            type_alerte="TEMPERATURE_ELEVEE",
            niveau="ELEVE",
            statut="ACTIVE",
            message="Alerte Colombie",
            valeur_detectee=30.0,
            seuil_minimum=23.0,
            seuil_maximum=29.0,
            date_declenchement=datetime.now(UTC),
            email_envoye=False,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(alerte_col)
        db.commit()
        cible_id = alerte_col.id

    reponse = client.patch(f"/alertes/{cible_id}", headers=utilisateurs["qualite_bra"], json={"statut": "RESOLUE"})
    assert reponse.status_code == 403


def test_alerte_inexistante_404(client, en_tete_admin):
    import uuid

    reponse = client.patch(f"/alertes/{uuid.uuid4()}", headers=en_tete_admin, json={"statut": "RESOLUE"})
    assert reponse.status_code == 404
