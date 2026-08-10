# tests/test_auth.py
"""Connexion, déconnexion, protection des routes et profil /auth/me."""


def test_login_admin_retourne_token_et_profil(client):
    reponse = client.post(
        "/auth/login",
        json={"email": "admin@futurekawa.com", "mot_de_passe": "admin1234"},
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["access_token"]
    assert corps["token_type"] == "bearer"
    assert corps["utilisateur"]["role"] == "ADMIN_SIEGE"
    assert corps["utilisateur"]["pays_id"] is None


def test_login_email_inconnu_401(client):
    reponse = client.post(
        "/auth/login",
        json={"email": "inconnu@futurekawa.com", "mot_de_passe": "admin1234"},
    )
    assert reponse.status_code == 401


def test_login_mot_de_passe_invalide_401(client):
    reponse = client.post(
        "/auth/login",
        json={"email": "admin@futurekawa.com", "mot_de_passe": "mauvais"},
    )
    assert reponse.status_code == 401


def test_login_compte_desactive_403(client, pays_reference):
    from tests.conftest import creer_utilisateur

    creer_utilisateur("desactive@futurekawa.com", "REFERENT_QUALITE", actif=False, pays_id=pays_reference["BRA"].id)
    reponse = client.post(
        "/auth/login",
        json={"email": "desactive@futurekawa.com", "mot_de_passe": "motdepasse1"},
    )
    assert reponse.status_code == 403


def test_me_retourne_profil(client, en_tete_admin):
    reponse = client.get("/auth/me", headers=en_tete_admin)
    assert reponse.status_code == 200
    assert reponse.json()["email"] == "admin@futurekawa.com"


def test_me_sans_token_401(client):
    assert client.get("/auth/me").status_code == 401


def test_token_invalide_401(client):
    reponse = client.get("/auth/me", headers={"Authorization": "Bearer token.faux.inexistant"})
    assert reponse.status_code == 401


def test_toutes_les_routes_de_donnees_exigent_authentification(client):
    for chemin in ("/pays", "/lots", "/alertes", "/entrepots", "/capteurs", "/mesures", "/synchronisations"):
        assert client.get(chemin).status_code == 401, chemin
