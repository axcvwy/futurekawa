# Plan de tests — FutureKawa

Ce document décrit la stratégie de test du projet, la typologie, les cas de test
automatisés, les jeux de données, les critères de réussite et la gestion des
anomalies. Il accompagne les tests exécutables : `./scripts/test-all.sh`.

---

## 1. Stratégie & typologie

**Objectif** : garantir que l'application couvre le cahier des charges —
supervision des entrepôts par pays, alertes (température/humidité, lots > 365 j),
synchronisation entre Siège et nœuds pays, et console web du Siège.

| Typologie | Outil | Périmètre |
|---|---|---|
| **Unitaires** | pytest (Python) | Logique métier : seuils d'alerte, déduplication anti-spam, résolution automatique, lots trop anciens. |
| **Intégration / API** | pytest + `fastapi.testclient.TestClient` | Endpoints REST des backends local & central (auth, mesures, CRUD, périphériques). |
| **Synchronisation** | pytest (moteur `syncer`) | Idempotence des upserts (pays_id, source_id), journalisation. |
| **UI (composants)** | Vitest + `@vue/test-utils` | Composants Vue : badges de statut/niveau, pages. |
| **End-to-end manuel** | scripts + doc `tests-manuels.md` | Chaîne complète ESP32 → MQTT → Node-RED → backend local → central → frontend. |

### Bases de données de test

Les suites s'exécutent sur des bases PostgreSQL dédiées, isolées de la production :

| Suite | Base | Piloté par |
|---|---|---|
| Backend local | `futurekawa_local_test` | `local-country/backend/tests/conftest.py` (variable `TEST_DATABASE_URL`) |
| Backend central | `futurekawa_central_test` | `central-backend/tests/conftest.py` (variable `TEST_DATABASE_URL`) |

Les envois d'e-mails réels sont **neutralisés** (mock en mémoire) pendant les tests.

### Lancement

```bash
./scripts/test-all.sh          # les 3 suites
./scripts/test-local.sh        # backend local (pytest)
./scripts/test-central.sh      # backend central (pytest)
./scripts/test-frontend.sh     # Vitest + build de production
```

---

## 2. Cas de tests automatisés

### 2.1 Backend local (Colombie) — `local-country/backend/tests/`

Bande idéale Colombie : **26 ± 3 °C** (23–29 °C), humidité **80 ± 2 %** (78–82 %).

| ID | Type | Fichier / Test | Scénario | Données de test | Critère de réussite |
|---|---|---|---|---|---|
| AUT-LOC-01 | Unitaire | `test_alertes_conditions.py::test_temperature_normal_no_alert` | Température normale | 26 °C / 80 % | 0 alerte créée, aucun e-mail |
| AUT-LOC-02 | Unitaire | `test_temperature_high_creates_one_alert_and_email` | Température haute | 30 °C / 80 % | 1 alerte `TEMPERATURE_ELEVEE` ACTIVE, `email_envoye=True`, 1 e-mail |
| AUT-LOC-03 | Unitaire | `test_repeated_high_temperature_does_not_duplicate_alerts_or_emails` | Répétition haute | 30 °C puis 31 °C | Toujours 1 alert stationnelle + 1 seul e-mail (aucun doublon) |
| AUT-LOC-04 | Unitaire | `test_temperature_recovers_resolves_alert` | Retour à la normale | 30 °C puis 26 °C | Alerte `RESOLUE`, `date_resolution` renseignée |
| AUT-LOC-05 | Unitaire | `test_humidity_high_creates_alert` | Humidité hors bande | 26 °C / 85 % | 1 alerte `HUMIDITE_ELEVEE` |
| AUT-LOC-06 | Unitaire | `test_lots_anciens.py::test_lot_trop_ancien_creates_alert` | Lot > 365 jours | `date_stockage = J-366` | 1 alerte `LOT_TROP_ANCIEN`, e-mail au responsable, lot → `PERIME` |
| AUT-LOC-07 | Unitaire | `test_lot_trop_ancien_idempotent` | Re-jeu vérification | même lot ancien 2× | Toujours 1 alerte + 1 e-mail |
| AUT-LOC-08 | Unitaire | `test_lot_recent_no_alert` | Lot récent | `date_stockage = aujourd'hui` | Aucune alerte, aucun e-mail |
| AUT-LOC-09 | API | `test_mesures_api.py::test_post_mesures_persists_data_by_topic` | Post mesure par topic MQTT | `topic_mqtt` connu, 26.5 °C / 80 % | 201, ligne `mesures` reliée à `entrepot_id` + `capteur_id` |
| AUT-LOC-10 | API | `test_post_mesures_unknown_topic_404` | Topic inconnu | `futurekawa/col/inconnu` | 404 |
| AUT-LOC-11 | API | `test_post_mesures_requires_api_key` | Appel sans clé | pas d'en-tête `X-API-Key` | 401 |
| AUT-LOC-12 | API | `test_post_mesures_incoherent_entrepot_400` | entrepot_id incohérent | id différent du capteur | 400 |
| AUT-LOC-13 | API | `test_post_mesures_alerts_on_high_temperature` | Circuit complet route + service | 33 °C / 80 % | 201 + 1 alerte `TEMPERATURE_ELEVEE` créée |

### 2.2 Backend central (Siège) — `central-backend/tests/`

| ID | Type | Fichier / Test | Scénario | Critère de réussite |
|---|---|---|---|---|
| AUT-CEN-01 | Synchronisation | `test_synchronisation.py::test_sync_upserts_without_duplicates` | 2 passes synchrones pays BRA (mock) | Journaux `SUCCES` ; compteurs identiques après re-jeu (1 entrepôt, 1 capteur, 3 lots, 4 mesures, 2 alertes) — pas de doublon |
| AUT-CEN-02 | Synchronisation | `test_sync_enregistre_un_journal_par_passe` | Exécution d'une synchro | 1 ligne `Synchronisation` avec `statut=SUCCES`, `declencheur=MANUEL` |
| AUT-CEN-03 | Intégration / RBAC | `test_auth.py` (7 tests) | Connexion, profils, routes protégées | tokens valides/invalides, comptes désactivés, 401 partout sans token |
| AUT-CEN-04 | Intégration / Périmètres | `test_perimetres.py` (8 tests) | Isolement des données par rôle | Un utilisateur COL ne voit pas les lots/alertes BRA ; responsable entrepôt scopé sur son entrepôt |
| AUT-CEN-05 | Intégration / Alertes | `test_alertes.py` (10 tests) | Cycle de vie des alertes + RBAC | Transitions de statut, règles par rôle |
| AUT-CEN-06 | Intégration / Écritures | `test_ecritures.py` (7 tests) | Config pays, exploitations, entrepôts, capteurs | Créations autorisées à `ADMIN_SIEGE` uniquement |
| AUT-CEN-07 | Intégration / Utilisateurs | `test_utilisateurs.py` (13 tests) | CRUD utilisateurs | Rubriques, 409 doublons, 400, impossibilité de supprimer son compte |
| AUT-CEN-08 | Intégration / Lots | `test_lots.py` (8 tests) | Création/mutation des lots | Périmètre, statuts, mode simulation 400 |

### 2.2bis Flux d'intégration ERP — `central-backend/app/routes/erp.py`

Contrats plats orientés consommateur externe (SAP / MS Dynamics / mock), authentifiés
par header `X-ERP-Key` (aucun compte JWT) : stocks consolidés, alertes qualité,
historique de mesures. Cf. `tests/test_erp.py`.

| ID | Type | Fichier / Test | Scénario | Critère de réussite |
|---|---|---|---|---|
| AUT-ERP-01 | Sécurité | `test_erp_sans_cle_repond_401` | Appel `/erp/stocks` sans header | 401 |
| AUT-ERP-02 | Sécurité | `test_erp_avec_mauvaise_cle_repond_401` | Clé X-ERP-Key invalide | 401 |
| AUT-ERP-03 | Intégration / Stock | `test_erp_stocks_consolides` | Lot BRA + alerte ACTIVE + 1 mesure | Contrat complet : pays, exploitation, entrepôt, `active_alert_count=1`, dernières T°/H% |
| AUT-ERP-04 | Intégration / Stock | `test_erp_stock_lot_inconnu_404` | Code lot inexistant `LOT-INCONNU` | 404 |
| AUT-ERP-05 | Intégration / Alertes | `test_erp_alertes_consolidees` | Alerte BRA ACTIVE | `type/level/status`, `lot_id` métier, `detected_value` |
| AUT-ERP-06 | Intégration / Mesures | `test_erp_mesures_historique` | 2 mesures CAP-BRA-001 | Historique ordonné (récent → ancien), capteur rattaché |

**Total backend central : 59 tests (51 existants + 2 synchronisation + 6 flux ERP).**

### 2.3 Frontend central — `central-frontend/tests/`

| ID | Type | Fichier / Test | Scénario | Critère de réussite |
|---|---|---|---|---|
| AUT-UI-01 | UI | `badges.spec.ts::BadgeNiveau` (3) | Libellés ELEVE/MOYEN/inconnu | Texte français correct ou repli |
| AUT-UI-02 | UI | `badges.spec.ts::BadgeStatutLot` (2) | Libellé EN_STOCK / undefined | Texte lisible `en stock` / repli `inconnu` |
| AUT-UI-03 | Build | `npm run build` (vue-tsc + vite) | Compilation types + bundle | `✓ built` sans erreur |

---

## 3. Couverture par besoin du cahier des charges

| Besoin | Tests de référence |
|---|---|
| Surveillance température/humidité (III.4.1) | AUT-LOC-01 à 05, 13 |
| Lot trop ancien > 365 j (III.4.2) | AUT-LOC-06 à 08 |
| Alerte par e-mail au responsable | AUT-LOC-02, 06, 07 (mock e-mail) |
| Anti-spam (1 e-mail par incident) | AUT-LOC-03, 07 |
| Collecte MQTT / Node-RED → API locale | AUT-LOC-09 à 12 |
| Synchronisation Siège ⇄ pays | AUT-CEN-01, 02 |
| Authentification & RBAC (rôles) | AUT-CEN-03 à 07 |
| Intégration ERP : stocks / alertes / mesures (X-ERP-Key) | AUT-ERP-01 à 06 |
| Console web Siège | AUT-UI-01 à 03 |

---

## 4. Gestion des anomalies (constat → correction → re-test)

| ID | Anomalie constatée | Correction appliquée | Re-test | Résultat |
|---|---|---|---|---|
| ANO-01 | Un e-mail était envoyé à chaque mesure en dérive (spam, toutes les ~30 s) | Déduplication : 1 seule alerte ACTIVE par `entrepot + capteur + type` ; e-mail uniquement à la 1re détection | AUT-LOC-03, MAN-06 | OK |
| ANO-02 | Une alerte ne revenait jamais à la normale : aucune résolution automatique après retour des valeurs dans la bande | Ajout de `resoudre_alertes_retablies` : passage automatique à `RESOLUE` + `date_resolution` | AUT-LOC-04 | OK |
| ANO-03 | Aucune mesure sur la page lot pour un capteur d'entrepôt | Requête des mesures par entrepôt filtée par `date_mesure ≥ date_stockage` du lot | MAN-09 | OK |
| ANO-04 | Node-RED ne persistait pas les mesures (aucun forward HTTP) | Ajout d'un nœud Function → `POST /mesures/` avec `X-API-Key` | MAN-03 | OK |
| ANO-05 | E-mail adressé à la config pays (placeholder) au lieu du responsable entrepôt | Priorité à `entrepôt.email_responsable` puis repli pays | AUT-LOC-02, 06 | OK |
| ANO-06 | La synchronisation pouvait dupliquer les lignes en cas de re-jeu | Upsert idempotent sur `(pays_id, source_id)` | AUT-CEN-01 | OK |

_Certaines anomalies (ANO-03/04) relèvent du manuel : voir `docs/tests-manuels.md`._

---

## 5. Rapport de tests

Les sorties des suites (pytest / Vitest / build) tiennent lieu de rapport :

- Backend local : `py.test` → `14 passed`
- Backend central : `py.test` → `59 passed` (dont 6 du flux ERP)
- Frontend : `vitest run` → `5 passed` puis `npm run build` → ✓ built

Le script `./scripts/test-all.sh` aggrège les trois et affiche un résumé final.