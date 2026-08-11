# app/services/scheduler.py
"""
Planificateur asynchrone : déclenche automatiquement la synchronisation des pays
dont l'intervalle est dépassé (par défaut toutes les 5 minutes).
"""

import asyncio
import datetime
import logging

from app.config import SCHEDULER_POLL_SECONDS
from app.database.db import SessionLocal
from app.models.pays import Pays
from app.services.syncer import synchronize_pays

logger = logging.getLogger(__name__)


def run_due_syncs() -> None:
    """Lance la synchro de chaque pays actif dont l'échéance est atteinte."""
    db = SessionLocal()
    try:
        now = datetime.datetime.now(datetime.UTC)
        for pays in db.query(Pays).filter(Pays.actif.is_(True)).all():
            due = pays.derniere_sync_reussie_le is None
            if not due:
                elapsed = (now - pays.derniere_sync_reussie_le).total_seconds()
                due = elapsed >= pays.intervalle_sync_secondes
            if not due:
                continue
            try:
                synchronize_pays(db, pays, declencheur="AUTOMATIQUE")
                db.commit()
                logger.info("Synchro automatique %s terminée : %s", pays.code_iso, pays.dernier_statut_sync)
            except Exception:
                db.rollback()
                logger.exception("Échec automatique pour %s", pays.code_iso)
    finally:
        db.close()


async def scheduler_loop() -> None:
    """Boucle infinie de réveil du planificateur."""
    logger.info("Planificateur de synchronisation démarré (réveil toutes les %ss)", SCHEDULER_POLL_SECONDS)
    while True:
        try:
            run_due_syncs()
        except Exception:
            logger.exception("Erreur du cycle planificateur")
        await asyncio.sleep(SCHEDULER_POLL_SECONDS)
