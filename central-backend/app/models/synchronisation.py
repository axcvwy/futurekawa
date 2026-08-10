# app/models/synchronisation.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid, func

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Synchronisation(UUIDTimestampMixin, Base):
    """Journal de chaque exécution de synchronisation (automatique ou manuelle)."""

    __tablename__ = "synchronisations"

    pays_id = Column(Uuid(as_uuid=True), ForeignKey("pays.id", ondelete="CASCADE"), nullable=False, index=True)
    declencheur = Column(String(30), nullable=False)  # AUTOMATIQUE / MANUEL
    statut = Column(String(30), nullable=False, default="EN_COURS")  # EN_COURS / SUCCES / SUCCES_PARTIEL / ECHEC
    demarree_le = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    terminee_le = Column(DateTime(timezone=True), nullable=True)
    curseur_depart = Column(DateTime(timezone=True), nullable=True)
    curseur_arrivee = Column(DateTime(timezone=True), nullable=True)
    entrepots_lus = Column(Integer, nullable=False, default=0)
    entrepots_ecrits = Column(Integer, nullable=False, default=0)
    capteurs_lus = Column(Integer, nullable=False, default=0)
    capteurs_ecrits = Column(Integer, nullable=False, default=0)
    lots_lus = Column(Integer, nullable=False, default=0)
    lots_ecrits = Column(Integer, nullable=False, default=0)
    mesures_lues = Column(Integer, nullable=False, default=0)
    mesures_ecrites = Column(Integer, nullable=False, default=0)
    alertes_lues = Column(Integer, nullable=False, default=0)
    alertes_ecrites = Column(Integer, nullable=False, default=0)
    erreur = Column(Text, nullable=True)
