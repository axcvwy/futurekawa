# app/models/alerte.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Alerte(UUIDTimestampMixin, Base):
    """Copie centrale d'une alerte générée par un nœud local."""

    __tablename__ = "alertes"
    __table_args__ = (
        UniqueConstraint("pays_id", "source_id", name="uq_alertes_pays_source"),
        Index("ix_alertes_statut", "statut"),
        Index("ix_alertes_pays_date", "pays_id", "date_declenchement"),
    )

    pays_id = Column(Uuid(as_uuid=True), ForeignKey("pays.id", ondelete="CASCADE"), nullable=False, index=True)
    entrepot_id = Column(Uuid(as_uuid=True), ForeignKey("entrepots.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_id = Column(Uuid(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)
    capteur_id = Column(Uuid(as_uuid=True), ForeignKey("capteurs.id", ondelete="SET NULL"), nullable=True, index=True)
    source_id = Column(Uuid(as_uuid=True), nullable=False)  # UUID local original
    type_alerte = Column(String(50), nullable=False)
    niveau = Column(String(20), nullable=False, default="MOYEN")
    statut = Column(String(30), nullable=False, default="ACTIVE")
    message = Column(Text, nullable=False)
    valeur_detectee = Column(Numeric(10, 2), nullable=True)
    seuil_minimum = Column(Numeric(10, 2), nullable=True)
    seuil_maximum = Column(Numeric(10, 2), nullable=True)
    date_declenchement = Column(DateTime(timezone=True), nullable=False)
    date_resolution = Column(DateTime(timezone=True), nullable=True)
    resolue_par = Column(Uuid(as_uuid=True), nullable=True)
    commentaire_resolution = Column(Text, nullable=True)
    email_envoye = Column(Boolean, nullable=False, default=False)
    date_email = Column(DateTime(timezone=True), nullable=True)
    source_cree_le = Column(DateTime(timezone=True), nullable=False)
    source_mis_a_jour_le = Column(DateTime(timezone=True), nullable=False)
    synchronise_le = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pays = relationship("Pays")
    entrepot = relationship("Entrepot")
    lot = relationship("Lot")
    capteur = relationship("Capteur")
