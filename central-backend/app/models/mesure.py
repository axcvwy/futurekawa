# app/models/mesure.py
from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Mesure(UUIDTimestampMixin, Base):
    """Copie centrale d'une télémesure IoT locale."""

    __tablename__ = "mesures"
    __table_args__ = (
        UniqueConstraint("pays_id", "source_id", name="uq_mesures_pays_source"),
        Index("ix_mesures_pays_date", "pays_id", "date_mesure"),
        Index("ix_mesures_capteur_date", "capteur_id", "date_mesure"),
        Index("ix_mesures_entrepot_date", "entrepot_id", "date_mesure"),
    )

    pays_id = Column(Uuid(as_uuid=True), ForeignKey("pays.id", ondelete="CASCADE"), nullable=False, index=True)
    entrepot_id = Column(Uuid(as_uuid=True), ForeignKey("entrepots.id", ondelete="CASCADE"), nullable=False, index=True)
    capteur_id = Column(Uuid(as_uuid=True), ForeignKey("capteurs.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_id = Column(Uuid(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)
    source_id = Column(Uuid(as_uuid=True), nullable=False)  # UUID local original
    source = Column(String(30), nullable=False, default="MQTT")
    topic_mqtt = Column(String(255), nullable=False)
    date_mesure = Column(DateTime(timezone=True), nullable=False)
    date_reception = Column(DateTime(timezone=True), nullable=False)
    temperature_c = Column(Numeric(5, 2), nullable=False)
    humidite_pct = Column(Numeric(5, 2), nullable=False)
    donnees_brutes = Column(JSONB, nullable=True)
    source_cree_le = Column(DateTime(timezone=True), nullable=False)
    source_mis_a_jour_le = Column(DateTime(timezone=True), nullable=False)
    synchronise_le = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pays = relationship("Pays")
    entrepot = relationship("Entrepot")
    capteur = relationship("Capteur")
    lot = relationship("Lot")
