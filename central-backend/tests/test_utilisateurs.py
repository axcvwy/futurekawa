# tests/test_utilisateurs.py
"""Gestion des comptes utilisateurs (réservée à ADMIN_SIEGE)."""


def test_seul_admin_liste_les_utilisateurs(client, en_tete_admin, login, pays_reference):
    from tests.conftest import creer_utilisateur

    creer_utilisateur("resp@futurekawa.com", "RESPONSABLE_EXPLOITATION", pays_id=pays_reference["BRA"].id)
    reponse = client.get("/utilisateurs", headers=en_tete_admin)
    assert reponse.status_code == 200
    emails = [u["email"] for u in reponse.json()]
    assert "resp@futurekawa.com" in emails

    en_tete_resp = login(client, "resp@futurekawa.com")
    assert client.get("/utilisateurs", headers=en_tete_resp).status_code == 403


def test_creation_utilisateur_par_admin(client, en_tete_admin, pays_reference):
    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "nouveau@futurekawa.com",
            "nom": "Nouveau Responsable",
            "mot_de_passe": "s3cret-2024",
            "role": "RESPONSABLE_EXPLOITATION",
            "pays_id": str(pays_reference["BRA"].id),
        },
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["role"] == "RESPONSABLE_EXPLOITATION"
    assert corps["pays_id"] == str(pays_reference["BRA"].id)
    assert "mot_de_passe" not in corps


def test_creation_email_duplique_409(client, en_tete_admin, pays_reference):
    from tests.conftest import creer_utilisateur

    creer_utilisateur("doublon@futurekawa.com", "REFERENT_QUALITE", pays_id=pays_reference["BRA"].id)
    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "doublon@futurekawa.com",
            "nom": "Doublon",
            "mot_de_passe": "s3cret-2024",
            "role": "REFERENT_QUALITE",
            "pays_id": str(pays_reference["BRA"].id),
        },
    )
    assert reponse.status_code == 409


def test_role_invalide_400(client, en_tete_admin, pays_reference):
    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "role@futurekawa.com",
            "nom": "Mauvais rôle",
            "mot_de_passe": "s3cret-2024",
            "role": "DIRECTEUR_GENERAL",
            "pays_id": str(pays_reference["BRA"].id),
        },
    )
    assert reponse.status_code == 400


def test_non_admin_sans_pays_400(client, en_tete_admin):
    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "sanspays@futurekawa.com",
            "nom": "Sans pays",
            "mot_de_passe": "s3cret-2024",
            "role": "REFERENT_QUALITE",
        },
    )
    assert reponse.status_code == 400


def test_responsable_entrepot_doit_avoir_un_entrepot(client, en_tete_admin, pays_reference):
    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "ent.sans@futurekawa.com",
            "nom": "Entrepôt sans",
            "mot_de_passe": "s3cret-2024",
            "role": "RESPONSABLE_ENTREPOT",
            "pays_id": str(pays_reference["BRA"].id),
        },
    )
    assert reponse.status_code == 400


def test_responsable_entrepot_avec_perimetre_201(client, en_tete_admin, entrepot_bra):
    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "ent.valide@futurekawa.com",
            "nom": "Entrepôt valide",
            "mot_de_passe": "s3cret-2024",
            "role": "RESPONSABLE_ENTREPOT",
            "pays_id": str(entrepot_bra.pays_id),
            "entrepot_id": str(entrepot_bra.id),
        },
    )
    assert reponse.status_code == 201
    assert reponse.json()["entrepot_id"] == str(entrepot_bra.id)


def test_entrepot_inexistant_404(client, en_tete_admin, pays_reference):
    import uuid

    reponse = client.post(
        "/utilisateurs",
        headers=en_tete_admin,
        json={
            "email": "ent.faux@futurekawa.com",
            "nom": "Entrepôt faux",
            "mot_de_passe": "s3cret-2024",
            "role": "RESPONSABLE_ENTREPOT",
            "pays_id": str(pays_reference["BRA"].id),
            "entrepot_id": str(uuid.uuid4()),
        },
    )
    assert reponse.status_code == 404


def test_modification_perimetre(client, en_tete_admin, pays_reference):
    from tests.conftest import creer_utilisateur

    u = creer_utilisateur("mutable@futurekawa.com", "REFERENT_QUALITE", pays_id=pays_reference["BRA"].id)
    reponse = client.put(
        f"/utilisateurs/{u.id}",
        headers=en_tete_admin,
        json={"pays_id": str(pays_reference["COL"].id)},
    )
    assert reponse.status_code == 200
    assert reponse.json()["pays_id"] == str(pays_reference["COL"].id)


def test_impossible_de_supprimer_son_propre_compte(client, en_tete_admin, pays_reference):

    admin = None
    from app.database.db import SessionLocal
    from app.models.utilisateur import Utilisateur

    with SessionLocal() as db:
        admin = db.query(Utilisateur).filter(Utilisateur.email == "admin@futurekawa.com").first()
    reponse = client.delete(f"/utilisateurs/{admin.id}", headers=en_tete_admin)
    assert reponse.status_code == 400


def test_suppression_utilisateur(client, en_tete_admin, pays_reference):
    from tests.conftest import creer_utilisateur

    u = creer_utilisateur("a-supprimer@futurekawa.com", "REFERENT_QUALITE", pays_id=pays_reference["BRA"].id)
    reponse = client.delete(f"/utilisateurs/{u.id}", headers=en_tete_admin)
    assert reponse.status_code == 200
    assert client.get("/auth/me", headers=en_tete_admin).status_code == 200
