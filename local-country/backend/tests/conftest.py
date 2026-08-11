# tests/conftest.py
"""Fixtures pytest du backend local (pays).

Utilise une base PostgreSQL dédiée (futurekawa_local_test) pour isoler les tests
de la base de dev (futurekawa_local). L'envoi réel d'e-mails est neutralisé.
"""

import os
from datetime import UTC, date, datetime, timedelta

import pytest

# Bascule vers la base de test AVANT tout import de l'application
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://futurekawa:futurekawa@localhost:5432/futurekawa_local_test",
)
os.environ["API_KEY"] = "cle-test"
# Empêche la boucle de surveillance périodique de tourner pendant les tests
os.environ["ALERTE_LOTS_INTERVAL_SECONDS"] = "3600"

from app.database.db import Base, SessionLocal, engine
from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.pays import Pays
from app.services.seed import PAYS_DEFAULTS


@pytest.fixture(scope="session", autouse=True)
def _creer_tables():
    """Crée (ou vide) le schéma de test une seule fois pour toute la session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _nettoyer_entre_tests():
    """Supprime les lignes entre chaque test (ordre FK inverse), puis re-seed les pays."""
    with SessionLocal() as db:
        for modele in (Mesure, Alerte, Lot, Capteur, Entrepot, Pays):
            db.query(modele).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        for modele in (Mesure, Alerte, Lot, Capteur, Entrepot, Pays):
            db.query(modele).delete()
        db.commit()


@pytest.fixture(autouse=True)
def _donnees_base():
    """Garantit la configuration pays (Colombie, Brésil, Équateur) avant chaque test."""
    with SessionLocal() as db:
        if db.query(Pays).count() == 0:
            for donnees in PAYS_DEFAULTS:
                db.add(Pays(**donnees))
            db.commit()
    return True


@pytest.fixture(autouse=True)
def _neutraliser_envoi_email(monkeypatch):
    """Remplace l'envoi SMTP réel par un enregistreur en mémoire."""
    envoyes = []

    def _faux_email(to_email, subject, body):
        envoyes.append({"to": to_email, "subject": subject, "body": body})
        return True

    monkeypatch.setattr("app.services.alertes.send_real_email", _faux_email)
    return envoyes


@pytest.fixture(autouse=True)
def _neutraliser_boucle(monkeypatch):
    """Empêche la boucle asynchrone LOT_TROP_ANCIEN de tourner pendant les tests."""

    async def _noop():
        import asyncio

        while True:
            await asyncio.sleep(3600)

    monkeypatch.setattr("app.services.alertes.boucle_verification_lots_anciens", _noop)


app_dependency_override_installe = False


@pytest.fixture
def client():
    """TestClient FastAPI pointant sur la base de test."""
    global app_dependency_override_installe
    from app.database.db import get_db as _get_db
    from main import app

    if not app_dependency_override_installe:

        def _override():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[_get_db] = _override
        app_dependency_override_installe = True

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture
def en_tete_api() -> dict:
    return {"X-API-Key": "cle-test"}


@pytest.fixture
def pays_col(_donnees_base) -> Pays:
    with SessionLocal() as db:
        pays = db.query(Pays).filter(Pays.code_iso == "COL").first()
        if pays is not None:
            return pays
        # Repli défensif : garantit la config Colombie même si le seed a été vidé.
        for donnees in PAYS_DEFAULTS:
            db.add(Pays(**donnees))
        db.commit()
        return db.query(Pays).filter(Pays.code_iso == "COL").one()


@pytest.fixture
def entrepot_col(pays_col) -> Entrepot:
    with SessionLocal() as db:
        e = Entrepot(
            nom="Entrepôt Café Andin Medellín",
            ville="Medellín",
            code_pays="COL",
            nom_responsable="Laura Gómez",
            email_responsable="tue131098@protonmail.com",
            temperature_min_c=23.0,
            temperature_max_c=29.0,
            humidite_min_pct=78.0,
            humidite_max_pct=82.0,
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        return e


@pytest.fixture
def capteur_col(entrepot_col) -> Capteur:
    with SessionLocal() as db:
        c = Capteur(
            entrepot_id=entrepot_col.id,
            reference="ESP32-DHT22-COL-001",
            topic_mqtt="futurekawa/col/esp32-dht22-co-001",
            type_capteur="DHT22",
            statut="ACTIF",
            frequence_mesure_secondes=60,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c


@pytest.fixture
def lot_col(entrepot_col) -> Lot:
    with SessionLocal() as db:
        lot = Lot(
            code_lot="LOT-COL-2026-004",
            entrepot_id=entrepot_col.id,
            produit="Café Arabica Excelso",
            quantite_kg=1500.0,
            date_stockage=date.today(),  # lot récent, hors alerte
            statut="EN_STOCK",
        )
        db.add(lot)
        db.commit()
        db.refresh(lot)
        return lot


@pytest.fixture
def lot_ancien_col(entrepot_col) -> Lot:
    with SessionLocal() as db:
        lot = Lot(
            code_lot="LOT-COL-2023-999",
            entrepot_id=entrepot_col.id,
            produit="Café Green Ancient",
            quantite_kg=800.0,
            date_stockage=datetime.now(UTC).date() - timedelta(days=366),  # > 365 jours
            statut="EN_STOCK",
        )
        db.add(lot)
        db.commit()
        db.refresh(lot)
        return lot


@pytest.fixture
def db():
    """Session de base de test pour les assertions directes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
