# FutureKawa - Central Backend (Siège)

Ce dépôt contient le code source de l'**API Centrale (Siège)** de l'application de supervision et de traçabilité IoT de **FutureKawa**. 

Développé avec **FastAPI**, ce backend orchestre une architecture distribuée et hybride. Il permet la consolidation des données logistiques et IoT mondiales (Brésil, Colombie, Équateur) tout en respectant les critères d'indépendance des nœuds régionaux (Tolérance aux pannes réseau).

---

## 🏗️ Architecture du Projet & Principes Clefs

1. **Pattern API Gateway / Reverse Proxy** : Le Frontend communique uniquement avec cette API Centrale. Pour les actions d'écriture (`POST`, `DELETE`), le Siège aiguille et transfère de manière transparente les requêtes vers le backend local du pays concerné.
2. **Consolidation Directe (Supabase)** : Les routes de lecture (`GET`) interrogent directement les **vues PostgreSQL globales** (`vue_lots_fifo` et `vue_mesures_detaillees`) hébergées sur l'instance AWS/Supabase de production afin d'assurer des performances optimales et un tri FIFO en temps réel.
3. **Haute Disponibilité & Mode Hybride** : Le système intègre un mécanisme de bascule (`SHOULD_MOCK`) permettant de simuler l'activité des pays dont l'infrastructure n'est pas encore déployée (Brésil, Équateur) ou de pallier une coupure réseau grâce à une isolation par blocs `try/except`.

---

## 📁 Arborescence du Code

```text
futurekawa-central/
│
├── app/
│   ├── routes/
│   │   ├── __init__.py       # Package des routes centrales
│   │   ├── alertes.py        # Gestion du cycle de vie des alertes (GET, PATCH)
│   │   ├── mesures.py        # Historiques IoT pour Chart.js & simulation (GET, POST)
│   │   └── stocks.py         # Logistique et traçabilité FIFO des lots (GET, POST, DELETE)
│   │
│   ├── __init__.py
│   ├── config.py             # Paramètres réseau, BDD Supabase (psycopg2) & aiguillage
│   ├── main.py               # Point d'entrée FastAPI & Route de Heartbeat (/health)
│   └── mock_data.py          # Jeux de données simulés (Brésil, Équateur)
│
├── venv/                     # Environnement virtuel Python
├── .gitignore                # Fichiers exclus de Git (ex: venv, __pycache__)
├── Dockerfile                # Recette de conteneurisation pour le déploiement Jenkins
├── README.md                 # Documentation technique principale
└── requirements.txt          # Dépendances du projet (FastAPI, psycopg2-binary, requests)



# Installation des dépendances requises
pip install -r requirements.txt


#lancement de l'application
uvicorn app.main:app --reload --port 5001


# Tests
venv/bin/python -m pytest            # cf. tests/README.md


# Compte initial (dégradé, à changer en production)
#   ADMIN_EMAIL=admin@futurekawa.com  (variable d'environnement, défaut)
#   ADMIN_PASSWORD=admin1234          (variable d'environnement, défaut)

---

## 🔐 Authentification & Rôles (Console Siège)

Toutes les routes de données exigent un JWT (`Authorization: Bearer <token>`),
obtenu via `POST /auth/login`. Le hachage des mots de passe utilise bcrypt.

| Rôle | Périmètre | Droits d'écriture |
|---|---|---|
| `ADMIN_SIEGE` | Tous les pays | Configuration (pays, exploitations, entrepôts, capteurs), comptes, alertes, lots |
| `RESPONSABLE_EXPLOITATION` | Pays assigné | Créer/modifier lots, synchroniser son pays, traiter alertes |
| `RESPONSABLE_ENTREPOT` | Pays + entrepôt assignés | Créer/modifier lots de son entrepôt, acquitter alertes (pas résoudre/ignorer) |
| `REFERENT_QUALITE` | Pays assigné | Modifier le **statut** des lots (EN_ALERTE/CONFORME/A_VERIFIER), traiter alertes |

Les lectures (`GET`) sont restreintes au périmètre du rôle (filtre pays/entrepôt
appliqué à chaque requête). Les écritures passent par un **proxy** : le Siège
relaie vers le backend local du pays puis resynchronise le cache central.
Les pays en mode simulation (`mock=True`) refusent les écritures (400).

Endpoints de gestion des comptes (réservés à `ADMIN_SIEGE`) :
`GET/POST /utilisateurs`, `PUT/DELETE /utilisateurs/{id}`, `GET /auth/me`.

---

## 🏭 Endpoints exposés & Matrice CRUD

1. Consolidation Stocks (FIFO)
GET /api/central/stocks : Agrégation mondiale des stocks triés par date d'entrée (Algorithme FIFO).

POST /api/central/stocks/{country} : Gateway d'enregistrement d'un lot (Poussé au pays réel ou mocké).

DELETE /api/central/stocks/{country}/{lot_id} : Déclenchement de la sortie de stock suite à une vente.

2. Supervision des Alertes Groupe
GET /api/central/alertes : Monitoring global des anomalies de température, humidité et dépassement de seuil temporel (>365j).

PATCH /api/central/alertes/{country}/{alerte_id} : Traitement et acquittement des alertes par les opérateurs.

3. Métriques Temporelles IoT
GET /api/central/mesures/{country}/{capteur_id} : Extraction de l'historique chronologique structuré (Listes temporelles) pour l'intégration directe sur le Frontend via Chart.js.

POST /api/central/mesures/{country}/{capteur_id} : Injection manuelle de télémesures pour simuler des dérives thermiques en direct.

4. Vérification Santé (Heartbeat)
GET /health : Test de l'état de l'API Centrale et vérification de la connectivité réseau avec le nœud Équateur (Idéal pour l'automatisation des pipelines CI/CD Jenkins).