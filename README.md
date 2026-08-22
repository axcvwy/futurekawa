# FutureKawa

Monorepo du projet FutureKawa : supervision de la température / humidité des
entrepôts de café, de la capteur IoT jusqu'au tableau de bord du siège.

## Structure

| Dossier             | Rôle                                            |
| ------------------- | ----------------------------------------------- |
| `local-country/`    | Backend local d'un pays (+ Postgres, Mosquitto, Node-RED), Docker Compose |
| `central-backend/`  | Backend central (FastAPI), BDD Supabase          |
| `central-frontend/` | Interface web (Vue 3, Vite, TypeScript)          |

## Prérequis

- Docker + Docker Compose (pour `local-country/`)
- Python 3.11+ (pour `central-backend/`)
- Node.js 18+ (pour `central-frontend/`)

## Configuration des variables d'environnement

Chaque sous-projet garde son **propre** fichier `.env` (jamais commité) :

1. `cp central-backend/.env.example central-backend/.env` puis renseignez
   `DATABASE_URL` (Supabase) et `COL_API_KEY`.
2. `cp local-country/.env.example local-country/.env` puis renseignez
   `API_KEY`, `POSTGRES_*` et `SMTP_*` (Brevo).
3. Facultatif : `cp central-frontend/.env.example central-frontend/.env`
   pour `VITE_API_BASE_URL` (défaut `http://localhost:5001`).

## Lancement

### 1. Backend local (pays) — Docker Compose

```bash
cd local-country
docker compose up -d --build
```

Services exposés :

| Service  | Port  |
| -------- | ----- |
| API locale (FastAPI) | 8000 |
| PostgreSQL | 5432 |
| Mosquitto (MQTT) | 1883 |
| Node-RED | 1880 |

> Implémentez dans Node-RED le flux MQTT → HTTP qui poste les mesures à
> `POST http://localhost:8000/mesures/` (en-tête `X-API-Key`).

### 2. Backend central

```bash
cd central-backend
python3 -m venv venv && venv/bin/pip install -q -r requirements.txt
venv/bin/python -m uvicorn app.main:app --reload --port 5001
```

Tests : `venv/bin/python -m pytest`

### 3. Frontend

```bash
cd central-frontend
npm install
npm run dev        # http://localhost:5173
```

Build de production : `npm run build`

## Ports utiles

| Service | URL / Port |
| ------- | ---------- |
| Frontend | http://localhost:5173 |
| Backend central | http://localhost:5001 (docs : /docs) |
| Backend local | http://localhost:8000 (docs : /docs) |
| MQTT | 1883 |
| Node-RED | http://localhost:1880 |

## Comptes de démonstration

- Admin siège : `admin@futurekawa.com` / `admin1234`

## Pays

- Brésil (BRA) et Équateur (ECU) : mode **mock** (données simulées côté Siège).
- Colombie (COL) : pays **réel** connecté au backend local (via Node-RED).