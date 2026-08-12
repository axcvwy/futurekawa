# app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database.db import Base, SessionLocal, engine, get_db
from app.models.pays import Pays
from app.routes import (
    alerte,
    auth,
    capteur,
    entrepot,
    erp,
    exploitation,
    lot,
    mesure,
    pays,
    synchronisation,
)
from app.services.scheduler import scheduler_loop
from app.services.seed import seed_admin, seed_pays

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Création des tables centrales si absentes
    Base.metadata.create_all(bind=engine)

    # 2. Seed de la table pays (une seule fois) + compte admin initial
    db = SessionLocal()
    try:
        seed_pays(db)
        seed_admin(db)
        db.commit()
        for p in db.query(Pays).order_by(Pays.code_iso).all():
            logger.info("Pays configuré : %s (%s) actif=%s url=%s", p.nom, p.code_iso, p.actif, p.api_base_url)
    finally:
        db.close()

    # 3. Planificateur de synchronisation (toutes les 5 min par défaut)
    task = asyncio.create_task(scheduler_loop())
    yield
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


app = FastAPI(
    title="FutureKawa™ — Backend Central (Siège)",
    description="API centrale de consolidation multi-pays (Pull périodique + cache PostgreSQL + dashboard Siège)",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuration de la politique CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production à l'URL du Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montage des routes du Siège (le frontend ne contacte jamais les backends locaux)
app.include_router(auth.router)
app.include_router(pays.router)
app.include_router(exploitation.router)
app.include_router(entrepot.router)
app.include_router(capteur.router)
app.include_router(lot.router)
app.include_router(mesure.router)
app.include_router(alerte.router)
app.include_router(synchronisation.router)
app.include_router(erp.router)


@app.get("/", tags=["Vérification Santé (Heartbeat)"])
def health_check():
    return {
        "status": "OPERATIONAL",
        "context": "FutureKawa Central Headquarter Backend",
        "api_contract": "OpenAPI 3.0 / Swagger active on /docs",
    }


@app.get("/health", tags=["Vérification Santé (Heartbeat)"])
def health_detail(db: Session = Depends(get_db)):
    """État de l'API + fraîcheur de la synchronisation par pays.
    Permet au frontend (bannière) et au CI/CD de détecter une connexion perdue."""
    countries = []
    for p in db.query(Pays).order_by(Pays.code_iso).all():
        countries.append(
            {
                "code_iso": p.code_iso,
                "nom": p.nom,
                "actif": p.actif,
                "mock": p.mock,
                "dernier_statut_sync": p.dernier_statut_sync,
                "derniere_sync_reussie_le": p.derniere_sync_reussie_le,
                "derniere_erreur_sync": p.derniere_erreur_sync,
            }
        )
    return {"status": "OPERATIONAL", "base_de_donnees": "CONNECTEE", "pays": countries}
