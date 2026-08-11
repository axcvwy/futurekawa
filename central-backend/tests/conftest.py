# tests/conftest.py
"""Fixtures pytest du backend central.

Utilise une base PostgreSQL dédiée (futurekawa_central_test) sur le Postgres local
pour isoler les tests de la base Supabase de production.
"""

import asyncio
import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Bascule vers la base de test AVANT tout import de l'application
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://futurekawa:futurekawa@localhost:5432/futurekawa_central_test",
)

from app.core.security import hacher_mot_de_passe
from app.database.db import Base, SessionLocal, engine, get_db
from app.main import app
from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.exploitation import Exploitation
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.pays import Pays
from app.models.synchronisation import Synchronisation
from app.models.utilisateur import Utilisateur


@pytest.fixture(scope="session", autouse=True)
def _creer_tables():
    """Crée (ou vide) le schéma de test une seule fois pour toute la session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _nettoyer_entre_tests():
    """Supprime les lignes entre chaque test (ordre FK inverse), puis re-seed les données de base."""
    with SessionLocal() as db:
        # On vide d'abord si un test précédent a laissé des données (sauf le premier lancement)
        for modele in (
            Mesure,
            Alerte,
            Lot,
            Capteur,
            Entrepot,
            Synchronisation,
            Exploitation,
            Utilisateur,
            Pays,
        ):
            db.query(modele).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        for modele in (
            Mesure,
            Alerte,
            Lot,
            Capteur,
            Entrepot,
            Synchronisation,
            Exploitation,
            Utilisateur,
            Pays,
        ):
            db.query(modele).delete()
        db.commit()


@pytest.fixture(autouse=True)
def _donnees_base():
    """Garantit le compte admin + les pays de référence avant chaque test
    (le seed du lifespan ne tourne qu'une fois au démarrage du TestClient)."""
    from app.config import PAYS_DEFAULTS

    with SessionLocal() as db:
        if db.query(Utilisateur).count() == 0:
            db.add(
                Utilisateur(
                    email="admin@futurekawa.com",
                    nom="Administrateur Siège",
                    mot_de_passe_hash=hacher_mot_de_passe("admin1234"),
                    role="ADMIN_SIEGE",
                    actif=True,
                )
            )
        if db.query(Pays).count() == 0:
            for donnees in PAYS_DEFAULTS:
                db.add(Pays(**donnees))
        db.commit()


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    # On neutralise le planificateur (pas de sync automatique pendant les tests)
    import app.main as main_module

    async def _scheduler_noop():
        while True:
            await asyncio.sleep(3600)

    main_module.scheduler_loop = _scheduler_noop
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client) -> str:
    reponse = client.post(
        "/auth/login",
        json={"email": "admin@futurekawa.com", "mot_de_passe": "admin1234"},
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["access_token"]


@pytest.fixture
def en_tete_admin(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def pays_reference() -> dict[str, Pays]:
    """Les 3 pays de référence (déjà semés par _donnees_base)."""
    with SessionLocal() as db:
        return {p.code_iso: p for p in db.query(Pays).order_by(Pays.code_iso).all()}


@pytest.fixture
def exploitation_bra(client, pays_reference) -> Exploitation:
    with SessionLocal() as db:
        explo = Exploitation(
            pays_id=pays_reference["BRA"].id,
            source_id=uuid4(),
            nom="Fazenda Bahia",
            code="FB",
            ville="Salvador",
            actif=True,
        )
        db.add(explo)
        db.commit()
        db.refresh(explo)
        return explo


@pytest.fixture
def entrepot_bra(exploitation_bra) -> Entrepot:
    with SessionLocal() as db:
        e = Entrepot(
            pays_id=exploitation_bra.pays_id,
            exploitation_id=exploitation_bra.id,
            source_id=uuid4(),
            nom="Entrepôt Salvador",
            ville="Salvador",
            code_pays="BRA",
            nom_responsable="Maria Silva",
            email_responsable="maria@futurekawa.com",
            temperature_min_c=26.0,
            temperature_max_c=32.0,
            humidite_min_pct=53.0,
            humidite_max_pct=57.0,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        return e


@pytest.fixture
def capteur_bra(entrepot_bra) -> Capteur:
    with SessionLocal() as db:
        c = Capteur(
            pays_id=entrepot_bra.pays_id,
            entrepot_id=entrepot_bra.id,
            source_id=uuid4(),
            reference="CAP-BRA-001",
            topic_mqtt="futurekawa/bra/entrepot-1/temp",
            type_capteur="DHT22",
            statut="ACTIF",
            frequence_mesure_secondes=60,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c


@pytest.fixture
def lot_bra(entrepot_bra) -> Lot:
    with SessionLocal() as db:
        lot = Lot(
            pays_id=entrepot_bra.pays_id,
            entrepot_id=entrepot_bra.id,
            source_id=uuid4(),
            code_lot="LOT-BRA-2024-001",
            produit="Arabica Bahia",
            quantite_kg=1200.0,
            date_stockage=date(2024, 1, 10),
            statut="EN_STOCK",
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(lot)
        db.commit()
        db.refresh(lot)
        return lot


@pytest.fixture
def alerte_bra(entrepot_bra, capteur_bra, lot_bra) -> Alerte:
    with SessionLocal() as db:
        a = Alerte(
            pays_id=entrepot_bra.pays_id,
            entrepot_id=entrepot_bra.id,
            lot_id=lot_bra.id,
            capteur_id=capteur_bra.id,
            source_id=uuid4(),
            type_alerte="TEMPERATURE_ELEVEE",
            niveau="ELEVE",
            statut="ACTIVE",
            message="Température hors bande idéale du pays BRA",
            valeur_detectee=34.5,
            seuil_minimum=26.0,
            seuil_maximum=32.0,
            date_declenchement=datetime.now(UTC),
            email_envoye=False,
            source_cree_le=datetime.now(UTC),
            source_mis_a_jour_le=datetime.now(UTC),
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        return a


def creer_utilisateur(
    email: str, role: str, mot_de_passe: str = "motdepasse1", actif: bool = True, **perimetre
) -> Utilisateur:
    """Helper : crée un utilisateur directement en base (les rôles testés)."""
    with SessionLocal() as db:
        u = Utilisateur(
            email=email,
            nom=f"Utilisateur {role}",
            mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe),
            role=role,
            actif=actif,
            pays_id=perimetre.get("pays_id"),
            entrepot_id=perimetre.get("entrepot_id"),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u


@pytest.fixture
def login():
    def _login(client_: TestClient, email: str, mot_de_passe: str = "motdepasse1") -> dict:
        reponse = client_.post(
            "/auth/login",
            json={"email": email, "mot_de_passe": mot_de_passe},
        )
        assert reponse.status_code == 200, reponse.text
        return {"Authorization": f"Bearer {reponse.json()['access_token']}"}

    return _login


@pytest.fixture
def utilisateurs(login, client, pays_reference, entrepot_bra):
    """Un jeu de comptes par rôle + leurs en-têtes HTTP authentifiés."""
    creer_utilisateur("resp.bra@futurekawa.com", "RESPONSABLE_EXPLOITATION", pays_id=pays_reference["BRA"].id)
    creer_utilisateur("resp.col@futurekawa.com", "RESPONSABLE_EXPLOITATION", pays_id=pays_reference["COL"].id)
    creer_utilisateur("qualite.bra@futurekawa.com", "REFERENT_QUALITE", pays_id=pays_reference["BRA"].id)
    creer_utilisateur(
        "resp.ent@futurekawa.com",
        "RESPONSABLE_ENTREPOT",
        pays_id=pays_reference["BRA"].id,
        entrepot_id=entrepot_bra.id,
    )
    return {
        "resp_bra": login(client, "resp.bra@futurekawa.com"),
        "resp_col": login(client, "resp.col@futurekawa.com"),
        "qualite_bra": login(client, "qualite.bra@futurekawa.com"),
        "resp_ent": login(client, "resp.ent@futurekawa.com"),
    }
