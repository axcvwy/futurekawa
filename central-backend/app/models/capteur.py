# app/models/capteur.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Capteur(UUIDTimestampMixin, Base):
    """Copie centrale d'un capteur IoT local."""

    __tablename__ = "capteurs"
    __table_args__ = (
        UniqueConstraint("pays_id", "source_id", name="uq_capteurs_pays_source"),
    )

    pays_id = Column(Uuid(as_uuid=True), ForeignKey("pays.id", ondelete="CASCADE"), nullable=False, index=True)
    entrepot_id = Column(Uuid(as_uuid=True), ForeignKey("entrepots.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Uuid(as_uuid=True), nullable=False)  # UUID local original
    reference = Column(String(100), nullable=False)
    topic_mqtt = Column(String(255), nullable=False)
    type_capteur = Column(String(100), nullable=False)
    statut = Column(String(30), nullable=False, default="ACTIF")
    frequence_mesure_secondes = Column(Integer, nullable=False)
    derniere_communication = Column(DateTime(timezone=True), nullable=True)
    source_cree_le = Column(DateTime(timezone=True), nullable=False)
    source_mis_a_jour_le = Column(DateTime(timezone=True), nullable=False)
    synchronise_le = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pays = relationship("Pays")
    entrepot = relationship("Entrepot")
