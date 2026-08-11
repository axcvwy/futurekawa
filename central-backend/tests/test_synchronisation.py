# tests/test_synchronisation.py
"""Cas de tests — synchronisation pays : idempotence (pas de doublons) + traçage."""

import pytest

from app.config import PAYS_DEFAULTS
from app.database.db import SessionLocal
from app.models.alerte import Alerte
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.pays import Pays
from app.services.syncer import synchronize_pays


@pytest.fixture
def pays_bra():
    """Un pays Brésil (mock) stocké en base pour tester le moteur de synchronisation."""
    with SessionLocal() as db:
        donnees = next(d for d in PAYS_DEFAULTS if d["code_iso"] == "BRA")
        pays = db.query(Pays).filter_by(code_iso="BRA").first()
        if pays is None:
            pays = Pays(**donnees)
            db.add(pays)
            db.commit()
        db.refresh(pays)
        return pays


def test_sync_upserts_without_duplicates(pays_bra):
    """Deux synchronisations du même pays (data simulées BRA) → AUCUN doublon."""
    with SessionLocal() as db:
        pays = db.query(Pays).filter_by(id=pays_bra.id).one()

        # 1re passe : ingestion complète des données simulées du Brésil
        run1 = synchronize_pays(db, pays, declencheur="MANUEL")
        db.commit()

        assert run1.statut == "SUCCES"
        assert run1.entrepots_lus == 1
        assert run1.capteurs_lus == 1
        assert run1.lots_lus == 3
        assert run1.mesures_lues == 4
        assert run1.alertes_lues == 2

        compteurs_apres_1 = {
            "entrepots": db.query(Entrepot).filter_by(pays_id=pays.id).count(),
            "capteurs": db.query(Capteur).filter_by(pays_id=pays.id).count(),
            "lots": db.query(Lot).filter_by(pays_id=pays.id).count(),
            "mesures": db.query(Mesure).filter_by(pays_id=pays.id).count(),
            "alertes": db.query(Alerte).filter_by(pays_id=pays.id).count(),
        }

        # 2e passe : mêmes données renvoyées par le nœud local (re-jeu)
        run2 = synchronize_pays(db, pays, declencheur="MANUEL")
        db.commit()

        assert run2.statut == "SUCCES"
        compteurs_apres_2 = {
            "entrepots": db.query(Entrepot).filter_by(pays_id=pays.id).count(),
            "capteurs": db.query(Capteur).filter_by(pays_id=pays.id).count(),
            "lots": db.query(Lot).filter_by(pays_id=pays.id).count(),
            "mesures": db.query(Mesure).filter_by(pays_id=pays.id).count(),
            "alertes": db.query(Alerte).filter_by(pays_id=pays.id).count(),
        }

        # Le critère : identique après re-lecture (upsert sur pays_id + source_id).
        assert compteurs_apres_2 == compteurs_apres_1
        assert compteurs_apres_1["entrepots"] == 1
        assert compteurs_apres_1["capteurs"] == 1
        assert compteurs_apres_1["lots"] == 3
        assert compteurs_apres_1["mesures"] == 4
        assert compteurs_apres_1["alertes"] == 2


def test_sync_enregistre_un_journal_par_passe(pays_bra):
    """Chaque synchronisation écrit une ligne de journal Synchronisation."""
    with SessionLocal() as db:
        from app.models.synchronisation import Synchronisation

        pays = db.query(Pays).filter_by(id=pays_bra.id).one()
        synchronize_pays(db, pays, declencheur="MANUEL")
        db.commit()

        journaux = db.query(Synchronisation).filter_by(pays_id=pays.id).all()
        assert len(journaux) == 1
        assert journaux[0].statut == "SUCCES"
        assert journaux[0].declencheur == "MANUEL"
