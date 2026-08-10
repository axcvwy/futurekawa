# Tests du backend central (Siège)

Suite `pytest` couvrant l'authentification, la gestion des rôles, les périmètres
pays/entrepôt et les règles métier d'écriture (lots, alertes, config).

## Pré-requis

- Postgres local démarré (Docker Compose de `futurekawa-local`, port 5432).
- Une base `futurekawa_central_test` doit exister :

```bash
docker exec futurekawa-country-postgres psql -U futurekawa -d postgres \
  -c "CREATE DATABASE futurekawa_central_test"
```

> Les tests utilisent par défaut
> `postgresql+psycopg2://futurekawa:futurekawa@localhost:5432/futurekawa_central_test`.
> Pour la surcharger : `TEST_DATABASE_URL=...`.

## Lancement

```bash
cd futurekawa-central
venv/bin/python -m pytest            # tout
venv/bin/python -m pytest tests/test_auth.py -q
```

Le schéma est recréé automatiquement à chaque session (les tables de la base de
test sont vidées entre chaque test). La base Supabase de production n'est **jamais**
touchée par les tests.
