# Pipeline CI/CD — FutureKawa (Jenkins)

Ce document décrit le pipeline d'intégration et de déploiement continus du projet.
Il répond à l'exigence « CI/CD » du cahier des charges : **build, tests automatisés,
vérification de la qualité, packaging (images Docker / artefacts), artefacts prêts
pour la démo** — le tout dans un pipeline **documenté** et **exécuté** (journal de
build conservé comme preuve).

Le pipeline est déclaré dans `Jenkinsfile` (racine du dépôt).

---

## 1. Objectif et portée

| Exigence cahier des charges | Couverture dans la pipeline |
|---|---|
| Build | Frontend Vue (`npm ci` + `npm run build`) + images Docker des 2 backends. |
| Tests automatisés | Backend local (14 tests), backend central (53 tests), frontend (5 tests UI) — cf. `docs/plan-de-tests.md`. |
| Vérification de la qualité | `ruff check` + `ruff format --check` (lint + style) sur les 2 backends. |
| Packaging | Images Docker taguées (démo) + export en archives `.tar` ; build frontal Vite en `dist/`. |
| Artefacts prêts pour la démo | Dossier `artefacts/` : images exportables hors-ligne, frontend compilé, rapports de tests. |
| Preuve d'exécution | Journal complet du build consultable dans Jenkins ; liste des artefacts archivée. |

---

## 2. Vue d'ensemble du pipeline

```
[push/PR] ─▶ Récupération du code
           ─▶ Provisionnement des bases de test (Postgres 16 en conteneur)
           ─▶ Qualité du code (ruff check + format)          ── on échoue ici : pipeline rouge
           ─▶ Tests automatisés (3 branches parallèles)
           │      ├─ Backend local (pytest, 14 tests)
           │      ├─ Backend central (pytest, 53 tests)
           │      └─ Frontend (Vitest + build Vite)
           ─▶ Packaging images Docker (tag build-ID + latest)
           ─▶ Livraison des artefacts de démo (images .tar + dist/ + rapports)
           ─▶ Archivage dans Jenkins (archiveArtifacts)
```

---

## 3. Prérequis côté Jenkins

| Composant | Version / réglage |
|---|---|
| Agent | Machine avec **Docker**, **Python 3.12/3.13**, **Node 20+** et `npm`. |
| Plugin Jenkins | `Pipeline` (Declarative), `Credentials Binding`, `Artifacts` (embarqué). |
| Docker Registry | (optionnel) credentials Jenkins `dockerhub-futurekawa` pour un éventuel push. |
| Réseau | L'agent doit pouvoir lancer des conteneurs Docker (`docker run`). |

> Le port **5432** de l'agent ne doit pas être occupé pendant le job : le conteneur
> `futurekawa-testdb` le publie pour que les tests utilisent la même connexion que
> les scripts manuels (`scripts/test-*.sh`).

---

## 4. Étapes détaillées

### 4.1 Récupération du code
`checkout scm` : le monorepo (local-country + central-backend + central-frontend)
est rappatrié sur l'agent au commit pointé.

### 4.2 Provisionnement des bases de test
Un conteneur `postgres:16-alpine` est démarré (`futurekawa-testdb`, user/mdp
`futurekawa`) sur le port 5432, puis deux bases sont créées :
`futurekawa_local_test` et `futurekawa_central_test`. Les tests s'y connectent via
`TEST_DATABASE_URL` (déjà prévu par `tests/conftest.py` des deux backends).

### 4.3 Qualité du code
Les environnements virtuels sont recréés à l'identique des chemins des scripts
(`local-country/.venv`, `central-backend/venv`) puis :
- `ruff check app main.py tests` et `ruff format --check` (backend local) ;
- `ruff check app tests` et `ruff format --check` (backend central).

Toute règle de style/lint violée stoppe le pipeline.

### 4.4 Tests automatisés (parallèles)
| Branche | Commande | Résultat attendu |
|---|---|---|
| Backend local | `pytest -v` (14 tests) | 14 passed |
| Backend central | `pytest -v` (53 tests) | 53 passed |
| Frontend | `npm ci && npm run test -- --run` + `npm run build` | 5 tests passed + build Vite ok |

Chaque branche échoue indépendamment : le rapport final montre les suites en
succès / en échec.

### 4.5 Packaging des images Docker
Les deux backends sont construits en images Docker :
- `futurekawa/futurekawa-country-api:{tag}` (+ `:latest`) — contexte `local-country/backend` ;
- `futurekawa/futurekawa-central-backend:{tag}` (+ `:latest`) — contexte `central-backend`.

Le tag `{tag}` = `{BUILD_ID}-{GIT_COMMIT7}` : chaque build est traçable vers le
commit source.

### 4.6 Livraison des artefacts de démo
Dossier `artefacts/` assemblé puis archivé (`archiveArtifacts`) :
```
artefacts/
├── images/          futurekawa-country-api_<tag>.tar
│                    futurekawa-central-backend_<tag>.tar   (chargement hors-ligne : docker load)
├── frontend/        dist/ compilé par Vite (servable par nginx/any static host)
└── rapports/        journaux de tests (junit.xml si configurés)
```

### 4.7 Post-pipeline
- Le conteneur Postgres de test est systématiquement supprimé (`always`) ;
- le journal complet du build reste consultable dans l'historique Jenkins (preuve
  d'exécution).

---

## 5. Preuve d'exécution

1. **Journal de build** : chaque exécution du job laisse un log horodaté dans
   Jenkins (`Job → Build #N → Console Output`), archivé avec le résultat.
2. **Artefacts** : le dashboard du job liste `artefacts/**` — téléchargeable pour
   la démo sans reconstruire (images Docker + frontend compilé).
3. **Reproductibilité locale** : la suite est lancée hors Jenkins avec
   `./scripts/test-all.sh` (mêmes commandes, même résultat attendu), ce qui permet
   de démontrer l'exécution sans infrastructure Jenkins si nécessaire.

---

## 6. Gestion d'échec

| Symptôme | Cause probable | Action |
|---|---|---|
| Stage « Qualité du code » rouge | Règle ruff violée | `ruff check --fix` puis committer ; relancer. |
| Backend central en échec | Données/BD Supabase inaccessibles ou test flaky | Vérifier `TEST_DATABASE_URL` et le conteneur `futurekawa-testdb`. |
| Tests du frontend en échec | Snapshot/version Vue | Revoir `central-frontend/tests/badges.spec.ts`. |
| `docker build` en échec | Dépendance pip introuvable / réseau | Vérifier `requirements.txt` et l'accès PyPI sur l'agent. |

---

## 7. Fichiers liés

| Fichier | Rôle |
|---|---|
| `Jenkinsfile` | Déclaration déclarative de la pipeline (racine). |
| `scripts/test-all.sh` | Couverture automatisée équivalente hors Jenkins. |
| `local-country/backend/pyproject.toml`, `central-backend/pyproject.toml` | Config qualité (ruff). |
| `local-country/backend/Dockerfile`, `central-backend/Dockerfile` | Packaging des backends. |
| `.dockerignore` (2 backends) | Contexte de build allégé. |
| `docs/plan-de-tests.md` | Définition des tests exécutés dans la pipeline. |