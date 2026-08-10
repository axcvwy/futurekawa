# app/models/lot.py
from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Lot(UUIDTimestampMixin, Base):
    """Copie centrale d'un lot de café (table principale du FIFO Siège)."""

    __tablename__ = "lots"
    __table_args__ = (
        UniqueConstraint("pays_id", "source_id", name="uq_lots_pays_source"),
        UniqueConstraint("pays_id", "code_lot", name="uq_lots_pays_code_lot"),
    )

    pays_id = Column(Uuid(as_uuid=True), ForeignKey("pays.id", ondelete="CASCADE"), nullable=False, index=True)
    entrepot_id = Column(Uuid(as_uuid=True), ForeignKey("entrepots.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Uuid(as_uuid=True), nullable=False)  # UUID local original
    code_lot = Column(String(100), nullable=False)
    produit = Column(String(150), nullable=False)
    quantite_kg = Column(Numeric(12, 2), nullable=False)
    date_stockage = Column(Date, nullable=False)
    statut = Column(String(30), nullable=False, default="EN_STOCK")
    source_cree_le = Column(DateTime(timezone=True), nullable=False)
    source_mis_a_jour_le = Column(DateTime(timezone=True), nullable=False)
    synchronise_le = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pays = relationship("Pays")
    entrepot = relationship("Entrepot")
