# app/services/seed.py
import logging

from sqlalchemy.orm import Session

from app.config import PAYS_DEFAULTS
from app.core.security import hacher_mot_de_passe
from app.models.pays import Pays
from app.models.utilisateur import Utilisateur

logger = logging.getLogger(__name__)


def seed_pays(db: Session) -> None:
    """Insère les pays de référence uniquement si la table est vide."""
    if db.query(Pays).count() > 0:
        return
    for data in PAYS_DEFAULTS:
        db.add(Pays(**data))
    db.flush()
    logger.info("Table 'pays' initialisée avec %d pays", len(PAYS_DEFAULTS))


def seed_admin(db: Session) -> None:
    """Crée le compte ADMIN_SIEGE initial si aucun utilisateur n'existe.
    Les identifiants par défaut sont dégradés et doivent être changés en production
    (variable ADMIN_EMAIL / ADMIN_PASSWORD au lancement)."""
    if db.query(Utilisateur).count() > 0:
        return
    email = __import__("os").getenv("ADMIN_EMAIL", "admin@futurekawa.com")
    mot_de_passe = __import__("os").getenv("ADMIN_PASSWORD", "admin1234")
    db.add(
        Utilisateur(
            email=email,
            nom="Administrateur Siège",
            mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe),
            role="ADMIN_SIEGE",
            actif=True,
            pays_id=None,
            entrepot_id=None,
        )
    )
    db.flush()
    logger.info("Compte ADMIN_SIEGE initial créé : %s", email)
