# app/config.py
import os

from dotenv import load_dotenv

load_dotenv()


# Base de données PostgreSQL centrale (Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL manquante. Copiez .env.example vers .env puis renseignez la chaîne de connexion PostgreSQL centrale."
    )


# Paramètres de synchronisation (non sensibles, valeurs par défaut raisonnables)
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))       # 5 minutes
SYNC_OVERLAP_SECONDS = int(os.getenv("SYNC_OVERLAP_SECONDS", "120"))         # Fenêtre de recouvrement anti-frontière
SYNC_PAGE_SIZE = int(os.getenv("SYNC_PAGE_SIZE", "100"))                     # Pagination par page
SYNC_REQUEST_TIMEOUT = int(os.getenv("SYNC_REQUEST_TIMEOUT", "10"))          # Timeout HTTP par appel local
SCHEDULER_POLL_SECONDS = int(os.getenv("SCHEDULER_POLL_SECONDS", "30"))      # Cadence de réveil du planificateur

# Authentification (JWT) de la console Siège
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-a-changer-en-production")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "480"))     # 8 h


PAYS_DEFAULTS = [
    {
        "nom": "Brésil",
        "code_iso": "BRA",
        "api_base_url": os.getenv("BRA_API_BASE_URL", "http://localhost:8001"),
        "api_key": os.getenv("BRA_API_KEY", "mock-bresil"),
        "actif": True,
        "mock": True,
        "intervalle_sync_secondes": SYNC_INTERVAL_SECONDS,
        "temperature_cible_c": 29.0,
        "humidite_cible_pct": 55.0,
        "tolerance_temperature_c": 3.0,
        "tolerance_humidite_pct": 2.0,
    },
    {
        "nom": "Colombie",
        "code_iso": "COL",
        "api_base_url": os.getenv("COL_API_BASE_URL", "http://localhost:8000"),
        "api_key": os.getenv("COL_API_KEY", ""),
        "actif": True,
        "mock": False,
        "intervalle_sync_secondes": SYNC_INTERVAL_SECONDS,
        "temperature_cible_c": 26.0,
        "humidite_cible_pct": 80.0,
        "tolerance_temperature_c": 3.0,
        "tolerance_humidite_pct": 2.0,
    },
    {
        "nom": "Équateur",
        "code_iso": "ECU",
        "api_base_url": os.getenv("ECU_API_BASE_URL", "http://localhost:8000"),
        "api_key": os.getenv("ECU_API_KEY", "mock-equateur"),
        "actif": True,
        "mock": True,
        "intervalle_sync_secondes": SYNC_INTERVAL_SECONDS,
        "temperature_cible_c": 31.0,
        "humidite_cible_pct": 60.0,
        "tolerance_temperature_c": 3.0,
        "tolerance_humidite_pct": 2.0,
    },
]
