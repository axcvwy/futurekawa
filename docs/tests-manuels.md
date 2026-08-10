# Tests manuels FutureKawa

Ces tests complètent les tests automatisés (pytest / Vitest)

ESP32 → MQTT → Node-RED → backend local → backend central → console web du Siège.

Le préfixe `MAN-` = manuel. Les préfixes `AUT-*` renvoient au plan automatisé
(`docs/plan-de-tests.md`).

---

## 1. Prérequis

- Docker Desktop en cours d'exécution
- Fichier `.env` renseigné côté `local-country/` (clé API, SMTP/Brevo,
  `DATABASE_URL`, `ALERTE_LOTS_INTERVAL_SECONDS=60`)
- Fichier `.env` renseigné côté `central-backend/` (Supabase, `COL_API_KEY`)
- Variables d'env Node-RED : aucune clé requise ; la clé `X-API-Key` est
  intégrée au nœud Function du flow
- ESP32 + capteur DHT22 flashé, connecté au Wi-Fi, publiant sur le topic MQTT
  `futurekawa/col/esp32-dht22-co-001`
- Boîte e-mail de réception des alertes (responsable entrepôt)

## 2. Démarrage de l'environnement

```bash
# 1. Stack locale (Postgres + API + Mosquitto + Node-RED)
cd futurekawa/local-country
docker compose up --build

# 2. Backend central (Siège) — sur le port 5001
cd futurekawa/central-backend
venv/bin/python -m uvicorn app.main:app --port 5001 --reload

# 3. Frontend central — sur le port 5173
cd futurekawa/central-frontend
npm install
npm run dev
```

Points d'entrée utiles :

| Service | URL |
|---|---|
| API locale | `http://localhost:8000/docs` |
| API centrale | `http://localhost:5001/docs` |
| Mosquitto | `mqtt://localhost:1883` |
| Node-RED | `http://localhost:1880` |
| Console Siège | `http://localhost:5173` |
| Postgres local (host) | `localhost:5432` |

Compte de démonstration Siège : `admin@futurekawa.com` / `admin1234`

---

## 3. Cas de tests manuels

### MAN-01 — Ingestion d'une mesure en conditions normales

**But** : vérifier la chaîne complète sans fausse alerte.

1. Publier sur le broker une mesure normale :
   ```bash
   # via mosquitto_pub présent sur l'hôte
   mosquitto_pub -h localhost -t "futurekawa/col/esp32-dht22-co-001" \
     -m '{"temperature": 26.2, "humidity": 80}'
   ```
2. Constater dans Node-RED (onglet Debug) la mesure reçue et le POST
   `201` vers `http://host.docker.internal:8000/mesures/`.
3. Vérifier dans `http://localhost:8000/docs` : `GET /mesures/` montre la ligne
   avec `temperature_c=26.2`, `humidite_pct=80`.

**Critère de réussite** : aucune alerte créée, aucun e-mail reçu.

### MAN-02 — Mesure d'entrepôt (réception + message retour)

1. Imiter un appel API direct (équivalent Node-RED) :
   ```bash
   curl -s -X POST http://localhost:8000/mesures/ \
     -H "X-API-Key: VOTRE_CLE" \
     -H "Content-Type: application/json" \
     -d '{"topic_mqtt":"futurekawa/col/esp32-dht22-co-001","temperature_c":26.5,"humidite_pct":80}'
   ```
2. Réponse attendue : `{"status":"Mesure traitée","mesure_id":"..."}`.

**Critère de réussite** : statut 201 + ID renvoyé.

### MAN-03 — Déclenchement d'une alerte température élevée

**But** : vérifier détection + e-mail (correspond à AUT-LOC-02).

1. Publier une valeur hors bande : `{"temperature": 30.5, "humidity": 80}`.
2. Constater :
   - `GET /alertes/actives` expose une alerte `TEMPERATURE_ELEVEE` (niveau ELEVE,
     `statut=ACTIVE`) ;
   - la boîte du responsable reçoit l'e-mail "ALERTE ELEVE - TEMPERATURE_ELEVEE".

**Critère de réussite** : 1 alerte + 1 e-mail.

### MAN-04 — Retour à la normale → résolution automatique

1. Publier successivement 30.5 °C puis 26.2 °C.
2. Constater via `GET /alertes/{id}` (ou `/alertes/historique`) que le statut
   passe à `RESOLUE` avec `date_resolution` renseignée.

**Critère de réussite** : correspond à AUT-LOC-04 (résolution automatique).

### MAN-05 — Anti-spam e-mail (1 e-mail par incident)

1. Publier une mesure en dérive, attendre plusieurs cycles MQTT (~30 s).
2. Compter les alertes : toujours **une seule** alerte
   `TEMPERATURE_ELEVEE` ACTIVE pour ce capteur ; **un seul** e-mail reçu.

**Critère de réussite** : 1 alerte + 1 e-mail (pas de spam) ; cf. AUT-LOC-03.

### MAN-06 — Lot trop ancien (> 365 jours)

1. Insérer ou pointer un lot avec `date_stockage` il y a plus de 365 jours :
   ```bash
   docker exec -it futurekawa-country-postgres psql -U futurekawa -d futurekawa_local \
     -c "INSERT INTO lots (id, code_lot, entrepot_id, produit, quantite_kg, date_stockage, statut, cree_le, mis_a_jour_le)
         VALUES (gen_random_uuid(), 'LOT-MAN-TEST', '<entrepot_id>', 'Café test', 1000, CURRENT_DATE - 366, 'EN_STOCK', now(), now());"
   ```
2. Attendre la boucle (intervalle configuré, ex. 60 s) ou déclencher au
   démarrage.
3. Constater une alerte `LOT_TROP_ANCIEN` ACTIVE + e-mail au responsable, et le
   lot passé au statut `PERIME`.

**Critère de réussite** : 1 alerte + 1 e-mail ; cf. AUT-LOC-06.

### MAN-07 — Synchronisation locale → centrale

**But** : vérifier le transfert des données locales vers le Siège.

1. Créer/modifier un lot ou un entrepôt côté local (`POST /lots` avec la clé API).
2. Attendre le cycle de synchronisation du Siège (intervalle central configuré,
   défaut 300 s = 5 min ; pour un test rapide :
   `UPDATE pays SET intervalle_sync_secondes = 60 WHERE code_iso='COL';`).
3. Constater dans la console Siège (ou `GET http://localhost:5001/pays` puis les
   ressources) que le lot/entrepôt apparaît sans doublon.

**Critère de réussite** : données présentes côté central, identiques (cf. AUT-CEN-01).

### MAN-08 — Parcours complet console Siège

1. Ouvrir `http://localhost:5173` et se connecter avec le compte admin.
2. Sélectionner le pays **Colombie**.
3. Naviguer : Tableau de bord → entrée de l'entrepôt → onglet lots → page lot
   (courbes température/humidité + alertes) → page Alertes (acquitter, résoudre).
4. Vérifier que les données affichées correspondent aux mesures MQTT réelles.

**Critère de réussite** : navigation fluide, courbes et alertes à jour.

### MAN-09 — Test rapide de non-régression du build

```bash
./scripts/test-all.sh
```

**Critère de réussite** : les 3 suites passent (local, central, frontend + build).

---

## 4. Rédaction d'un compte-rendu

Pour chaque test effectué, consigner :

| Test | Date | Résultat (OK / KO) | Remarques |
|---|---|---|---|
| MAN-01 | ... | ... | ... |

En cas de KO : suivre la procédure de gestion des anomalies
(`docs/plan-de-tests.md` §4) — constat, correction, re-test.